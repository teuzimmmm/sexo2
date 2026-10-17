"""Explicit LCU imports with catalog validation and application-owned pages."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import threading
import time
import uuid

from lolalytics.item_pages import plan_item_pages
from utils.core.atomic_file import atomic_write

from .draft import BuildError, positive
from lcu.core.request_error import LCURequestError


def lcu_request(lcu,method,path,payload=None):
    try:return lcu.loadout_request(method,path,payload)
    except LCURequestError as error:raise BuildError(str(error)) from None


class GameCatalog:
    def __init__(self, lcu):
        self.lcu = lcu
        self._cache = {}
        self._revision = None

    def bind_revision(self, revision):
        if revision != self._revision:
            self._cache.clear()
            self._revision = revision

    def rows(self, name):
        if name not in self._cache:
            value = lcu_request(self.lcu,'GET', f'/lol-game-data/assets/v1/{name}.json')
            if name == 'perkstyles':
                if not isinstance(value, dict) or value.get('schemaVersion') != 2:
                    raise BuildError('A versão do catálogo de estilos de runas mudou.')
                rows = value.get('styles') if isinstance(value, dict) else None
            else:
                rows = value
            if not isinstance(rows, list) or not rows or len(rows) > 10000:
                raise BuildError('O catálogo de runas/itens mudou ou não está disponível.')
            self._cache[name] = rows
        return self._cache[name]

    def names(self, name):
        return {str(r['id']): str(r.get('name') or r.get('nameTRA') or r['id'])[:120]
                for r in self.rows(name) if isinstance(r, dict) and positive(r.get('id'))}


def canonical_item_sets(rows):
    """LCU serializes optional fields omitted by callers. Keep meaningful content.

    Based on LolItemSetsItemSet/Block; top-level order is not the item's order.
    Do not ignore blocks, counts, associations, user metadata, or duplicate UIDs.
    """
    if not isinstance(rows,list) or len(rows)>502:raise BuildError('Conjuntos de itens inválidos na confirmação.')
    result={}
    for value in rows:
        if not isinstance(value,dict) or not isinstance(value.get('uid'),str) or value['uid'] in result:
            raise BuildError('Identificadores de conjuntos ambíguos na confirmação.')
        row=deepcopy(value);row.setdefault('startedFrom','')
        blocks=row.get('blocks')
        if not isinstance(blocks,list):raise BuildError('Blocos de itens inválidos na confirmação.')
        for block in blocks:
            if not isinstance(block,dict):raise BuildError('Bloco de itens inválido na confirmação.')
            block.setdefault('hideIfSummonerSpell','');block.setdefault('showIfSummonerSpell','')
        result[row['uid']]=row
    return result


def _ids(values, count):
    if not isinstance(values, list) or len(values) != count:
        raise BuildError('A página de runas está incompleta.')
    result = []
    for value in values:
        if isinstance(value, bool) or not re.fullmatch(r'[1-9][0-9]{0,9}', str(value)):
            raise BuildError('A sugestão contém um identificador inválido.')
        result.append(int(value))
    return result


def rune_payload(page, styles, name):
    primary, secondary, mods = (_ids(page.runes.get(k), n) for k, n in [('pri', 4), ('sec', 2), ('mod', 3)])
    chosen = []
    for style in styles:
        slots = style.get('slots') if isinstance(style, dict) else None
        if not isinstance(style, dict) or not positive(style.get('id')) or not isinstance(slots, list) or len(slots) < 7:
            raise BuildError('O catálogo de estilos de runas mudou.')
        if any(not isinstance(s, dict) or not isinstance(s.get('perks'), list) for s in slots):
            raise BuildError('O catálogo de posições de runas mudou.')
        if all(perk in slots[i]['perks'] for i, perk in enumerate(primary)):
            if not all(perk in slots[i + 4]['perks'] for i, perk in enumerate(mods)):
                raise BuildError('Os fragmentos da sugestão não existem nessas posições no patch atual.')
            chosen.append(style['id'])
    if len(chosen) != 1:
        raise BuildError('As runas primárias não correspondem ao catálogo atual.')
    second = []
    for style in styles:
        if style['id'] == chosen[0]:
            continue
        slots = style['slots'][1:4]
        positions = [next((i for i, slot in enumerate(slots) if p in slot['perks']), None) for p in secondary]
        if None not in positions and len(set(positions)) == 2:
            second.append(style['id'])
    if len(second) != 1:
        raise BuildError('As runas secundárias não correspondem a duas posições válidas.')
    return {'name': name, 'primaryStyleId': chosen[0], 'subStyleId': second[0],
            'selectedPerkIds': primary + secondary + mods, 'current': True}


class LoadoutImporter:
    def __init__(self, lcu, state_path):
        self.lcu, self.path = lcu, Path(state_path)
        self.catalog = GameCatalog(lcu)
        self._lock = threading.Lock()
        self._owner = None
        self._state = None

    def _identity(self):
        if self._owner is None:
            if self.path.exists():
                if self.path.is_symlink() or self.path.stat().st_size > 4096:
                    raise BuildError('O registro das páginas gerenciadas não é válido.')
                try:
                    data = json.loads(self.path.read_text(encoding='utf-8'))
                    token = data['owner']
                    if data.get('schema') != 1 or not re.fullmatch(r'[0-9a-f]{32}', token):
                        raise ValueError()
                except (ValueError, KeyError, TypeError):
                    raise BuildError('Não foi possível ler o registro de páginas; nenhuma página pessoal será substituída.') from None
            else:
                token = uuid.uuid4().hex
                data = {'schema': 1, 'owner': token}
                with atomic_write(self.path) as file:
                    json.dump(data, file)
            mapping = data.get('runePages', {})
            if (not isinstance(mapping, dict) or len(mapping) > 16 or any(
                    not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{64}', key) or not positive(value)
                    for key, value in mapping.items())):
                raise BuildError('O registro de propriedade das páginas é inválido.')
            data['runePages'] = mapping
            self._state = data
            self._owner = token
        return self._owner

    def _account(self):
        current = lcu_request(self.lcu,'GET', '/lol-summoner/v1/current-summoner')
        if (not isinstance(current, dict) or not positive(current.get('summonerId'))
                or not positive(current.get('accountId'))):
            raise BuildError('Não foi possível identificar a conta conectada para importar.')
        return current['summonerId'], current['accountId']

    def apply(self, target, selected, pages, champion_id, *, guard, rune_page_id=None):
        with self._lock:
            context = guard()
            if isinstance(context, dict) and isinstance(context.get('revision'), str):
                self.catalog.bind_revision(context['revision'])
            account = self._account()

            def check():
                guard()
                if self._account() != account:
                    raise BuildError('A conta do cliente mudou. Consulte novamente.')

            try:
                if target == 'runes':
                    return self._runes(selected, account, check, rune_page_id=rune_page_id)
                if target == 'items':
                    return self._items(pages, champion_id, account, check)
                if target == 'item-groups':
                    return self._items_groups(pages, account, check)
                raise BuildError('Tipo de importação inválido.')
            except BuildError:
                raise
            except Exception:
                raise BuildError('A importação não foi confirmada. Confira as páginas no cliente antes de repetir.') from None

    def _runes(self, page, account, check, *, rune_page_id=None):
        self._identity()
        account_key = hashlib.sha256(f'{account[0]}:{account[1]}'.encode()).hexdigest()
        owned_id = self._state['runePages'].get(account_key)
        body = rune_payload(page, self.catalog.rows('perkstyles'), 'SEXO2 · ' + page.label[:35])
        path = '/lol-perks/v1/pages'
        previous = lcu_request(self.lcu,'GET', path)
        if not isinstance(previous, list) or any(not isinstance(p, dict) for p in previous):
            raise BuildError('Não foi possível ler suas páginas de runas.')
        if rune_page_id is not None:
            if not positive(rune_page_id):raise BuildError('Selecione uma página editável no LoL.')
            chosen=[p for p in previous if p.get('id')==rune_page_id and p.get('isEditable') is True]
            if len(chosen)!=1:raise BuildError('A página escolhida não está mais disponível ou é protegida.')
        else:chosen=[]
        owned = [p for p in previous if positive(owned_id) and p.get('id') == owned_id]
        if not chosen and (len(owned) > 1 or (owned and (owned[0].get('isEditable') is not True
                or not str(owned[0].get('name', '')).startswith('SEXO2 · ')))):
            raise BuildError('As páginas gerenciadas estão ambíguas ou protegidas. Nenhuma foi removida.')
        check()
        if lcu_request(self.lcu,'GET', path) != previous:
            raise BuildError('Suas páginas mudaram durante a importação. Tente novamente.')
        check()
        destination=chosen[0] if chosen else owned[0] if owned else None
        if chosen:self._backup_rune_page(account_key,chosen[0])
        endpoint = path + '/' + str(destination['id']) if destination else path
        try:
            response = lcu_request(self.lcu,'PUT' if destination else 'POST', endpoint, body)
        except BuildError:
            raise
        except ValueError:
            raise BuildError('O cliente não confirmou as runas. Escolha uma página editável existente no seletor ou libere espaço; nenhuma página foi apagada.') from None
        after = lcu_request(self.lcu,'GET', path)
        previous_ids = {p.get('id') for p in previous if positive(p.get('id'))}
        created_id = response.get('id') if isinstance(response, dict) else None
        target_id = destination['id'] if destination else created_id
        matches = [p for p in after if isinstance(p, dict) and positive(p.get('id'))
                   and (p['id'] == target_id if positive(target_id) else p['id'] not in previous_ids)
                   and p.get('name') == body['name']] if isinstance(after, list) else []
        if len(matches)==1 and all(matches[0].get(k)==v for k,v in body.items() if k!='current') and matches[0].get('current') is not True:
            check()
            lcu_request(self.lcu,'PUT','/lol-perks/v1/currentpage',matches[0]['id'])
            refreshed=lcu_request(self.lcu,'GET',path)
            matches=[p for p in refreshed if isinstance(p,dict) and positive(p.get('id')) and p.get('id')==matches[0]['id']] if isinstance(refreshed,list) else []
        if len(matches) != 1 or any(matches[0].get(k) != v for k, v in body.items()):
            raise BuildError('A escrita das runas não foi confirmada pela leitura do cliente. Confira a página no LoL.')
        # Ownership comes from our write + native ID, never from a display name alone.
        self._state['runePages'][account_key] = matches[0]['id']
        while len(self._state['runePages']) > 16:
            self._state['runePages'].pop(next(iter(self._state['runePages'])))
        with atomic_write(self.path) as file:
            json.dump(self._state, file)
        return {'target': 'runes', 'verified': True, 'message': 'Runas importadas e confirmadas no cliente.'}

    def rune_targets(self):
        rows=lcu_request(self.lcu,'GET','/lol-perks/v1/pages')
        if not isinstance(rows,list) or len(rows)>100:raise BuildError('Não foi possível ler as páginas de runas.')
        return [{'id':r['id'],'name':str(r.get('name') or 'Página de runas')[:100],
                 'current':r.get('current') is True}
                for r in rows if isinstance(r,dict) and positive(r.get('id')) and r.get('isEditable') is True]

    def _backup_rune_page(self,account_key,page):
        path=self.path.with_name('sexo2-rune-backups.json')
        if path.is_symlink() or (path.exists() and path.stat().st_size>65536):
            raise BuildError('O backup das runas não é válido; página preservada.')
        try:backups=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        except (ValueError,OSError):raise BuildError('Não foi possível preservar a página anterior.') from None
        if not isinstance(backups,dict) or len(backups)>16:raise BuildError('O backup das runas está inválido.')
        key=account_key+':'+str(page['id'])
        # Retain the original page across repeated imports, no account/player identity.
        if key not in backups:
            saved={k:deepcopy(page[k]) for k in ('name','primaryStyleId','subStyleId','selectedPerkIds','current') if k in page}
            if len(json.dumps(saved))>2048:raise BuildError('A página anterior excede o limite de backup.')
            backups[key]=saved
            while len(backups)>16:backups.pop(next(iter(backups)))
            with atomic_write(path) as file:json.dump(backups,file,ensure_ascii=False)

    def apply_item_groups(self, groups, *, guard):
        """At most two champion groups (the two lobby picks), same owned budget."""
        return self.apply('item-groups', None, groups, None, guard=guard)

    def _items(self, pages, cid, account, check):
        return self._items_groups([(cid, pages)], account, check)

    def _items_groups(self, groups, account, check):
        if (not isinstance(groups, (list, tuple)) or not 1 <= len(groups) <= 2
                or any(not isinstance(g, (list, tuple)) or len(g) != 2 or not positive(g[0])
                       or not isinstance(g[1], list) or not g[1] for g in groups)
                or len({g[0] for g in groups}) != len(groups)):
            raise BuildError('Campeões inválidos para os conjuntos de itens.')
        owner = uuid.UUID(self._identity())
        account_key = hashlib.sha256(f'{account[0]}:{account[1]}'.encode()).hexdigest()
        ids = [str(uuid.uuid5(owner, f'items:{account_key}:{slot}')) for slot in range(2)]
        known_items = self.catalog.names('items')
        sets = []
        for cid, pages in groups:
            if any(p.resolved.get('cid') != cid for p in pages):
                raise BuildError('O campeão dos itens não corresponde ao destino da importação.')
            prepared = plan_item_pages(pages, max_pages=1 if len(groups) == 2 else 2, max_blocks_per_page=20)
            for index, page in enumerate(prepared):
                blocks = []
                for prepared_block in page.blocks:
                    block = prepared_block.block
                    choices = []
                    for choice in block.choices:
                        if choice.identifier not in known_items or not positive(choice.count):
                            raise BuildError('Um item da sugestão não existe no catálogo atual do cliente.')
                        choices.append({'id': choice.identifier, 'count': choice.count})
                    # Preserve observed core order and explicit alternatives as distinct blocks.
                    metrics = block.metrics or (block.choices[0].metrics if len(block.choices) == 1 else {})
                    label = prepared_block.label
                    if metrics.get('games') is not None:
                        rate = metrics.get('win_rate')
                        if rate is not None:
                            label += f" · {rate}% / {metrics['games']} jogos"
                        elif metrics.get('pick_rate') is not None:
                            label += f" · PR {metrics['pick_rate']}% / {metrics['games']} jogos"
                        else:
                            label += f" · {metrics['games']} jogos"
                    elif len(block.choices) > 1 and not block.ordered and block.kind != 'suggested_core':
                        label += ' · alternativas'
                    blocks.append({'type': label, 'items': choices})
                sets.append({'uid': ids[len(sets)], 'title': 'SEXO2 · ' + page.title[:70],
                             'type': 'custom', 'map': 'any', 'mode': 'any', 'sortrank': 0,
                             'associatedChampions': [cid], 'associatedMaps': [11 if pages[0].query['mode'] in ('ranked', 'swift') else 12],
                             'preferredItemSlots': [], 'blocks': blocks})
        path = f'/lol-item-sets/v1/item-sets/{account[0]}/sets'
        before = lcu_request(self.lcu,'GET', path)
        if (not isinstance(before, dict) or before.get('accountId') != account[1]
                or not isinstance(before.get('itemSets'), list) or len(before['itemSets']) > 500):
            raise BuildError('O formato dos seus conjuntos de itens mudou ou está indisponível.')
        if any(not isinstance(s, dict) for s in before['itemSets']):
            raise BuildError('Há um conjunto de itens com formato inválido.')
        for row in before['itemSets']:
            if row.get('uid') in ids and not str(row.get('title', '')).startswith('SEXO2 · '):
                raise BuildError('Um conjunto gerenciado foi alterado manualmente. Nenhum conjunto pessoal foi substituído.')
        personal = [deepcopy(s) for s in before['itemSets'] if s.get('uid') not in ids]
        body = deepcopy(before)
        body.update(itemSets=personal + sets, timestamp=int(time.time() * 1000))
        check()
        if lcu_request(self.lcu,'GET', path) != before:
            raise BuildError('Seus conjuntos mudaram durante a importação. Tente novamente.')
        check()
        lcu_request(self.lcu,'PUT', path, body)
        after = lcu_request(self.lcu,'GET', path)
        if (not isinstance(after, dict) or after.get('accountId') != account[1]
                or canonical_item_sets(after.get('itemSets')) != canonical_item_sets(body['itemSets'])):
            raise BuildError('A escrita dos itens não foi confirmada. Confira os conjuntos no LoL.')
        return {'target': 'items', 'verified': True,
                'message': f'Itens confirmados em {len(sets)} conjunto(s) do SEXO2; conjuntos pessoais preservados.'}

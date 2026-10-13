from pathlib import Path
import hashlib
import json
import shutil

root = Path(__file__).resolve().parent
delivery = root.parent / 'rose-amigos-r5-1'
target = delivery / 'Rose'
shutil.copytree(root.parent / 'rose-amigos-r5' / 'Rose', target, dirs_exist_ok=True)
plugin = Path('Pengu Loader/plugins/ROSE-SwiftplayPins/index.js')
shutil.copy2(root / plugin, target / '_internal' / plugin)
(target / 'CORRECAO-ROLAGEM.txt').write_text(
    'Rose r5.1: correção da rolagem do seletor de skins Swiftplay.\n'
    'Atualizações sem mudanças preservam os elementos da lista.\n'
    'Mudanças de estado preservam busca, foco e rolagem para o mesmo campeão.\n'
    'Feche Rose e o cliente LoL antes de instalar. Preferências são preservadas.\n'
    'Painel BORK e hospedagem integrada ainda estão em planejamento.\n', encoding='utf-8')
manifest = {str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in target.rglob('*') if p.is_file() and p.name != 'manifesto.json'}
(target / 'manifesto.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(target / 'VERIFICACAO.json').write_text(json.dumps({
    'correcao': 'rolagem Swiftplay', 'teste_navegador': True,
    'sem_teste_em_partida_real': True, 'base': 'r5',
}), encoding='utf-8')
# Update the verification file digest after replacing its base report.
manifest['VERIFICACAO.json'] = hashlib.sha256((target / 'VERIFICACAO.json').read_bytes()).hexdigest()
(target / 'manifesto.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
spec = (root / 'installer-amigos-r5.iss').read_text(encoding='utf-8-sig')
spec = spec.replace('1.4.7.5', '1.4.7.6').replace('rose-amigos-r5', 'rose-amigos-r5-1')
spec = spec.replace('Rose Amigos r5 - Instalador', 'Rose r5.1 - Correcao Swiftplay')
spec = spec.replace('Rose dos Amigos r5 (base', 'Rose dos Amigos r5.1 (base')
(root / 'installer-scroll-fix.iss').write_text(spec, encoding='utf-8-sig')
print(delivery)

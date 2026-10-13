"""Rose Sala: host or join a friends relay without port forwarding or a VPN."""
import queue
import tkinter as tk
from tkinter import ttk,messagebox
from urllib.parse import urlsplit
from party.hosting.controller import HostController
from party.network.private_server_config import save_server_link,relay_settings

class SalaApp:
    def __init__(self,root):
        self.root=root;self.controller=HostController();self.closing=False
        root.title('Rose · Sala dos amigos');root.geometry('650x555');root.minsize(620,530)
        root.configure(background='#101820')
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('TFrame',background='#101820');style.configure('TLabel',background='#101820',foreground='#e4edf0',font=('Segoe UI',10))
        style.configure('Title.TLabel',font=('Segoe UI',20,'bold'),foreground='#72ddc9')
        style.configure('TButton',font=('Segoe UI',10),padding=8)
        frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Sala dos amigos',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text='Sem VPN. Sem abrir porta no roteador.').pack(anchor='w',pady=(3,18))
        ttk.Label(frame,text='Um de vocês hospeda; os outros usam o mesmo endereço.').pack(anchor='w')
        row=ttk.Frame(frame);row.pack(fill='x',pady=(10,8))
        self.host_button=ttk.Button(row,text='Hospedar uma sala',command=self.host);self.host_button.pack(side='left')
        self.stop_button=ttk.Button(row,text='Encerrar sala',command=self.stop,state='disabled');self.stop_button.pack(side='left',padx=8)
        self.status=tk.StringVar(value='Pronto para hospedar ou entrar na sala de um amigo.')
        ttk.Label(frame,textvariable=self.status,wraplength=590).pack(anchor='w',pady=(0,10))
        self.host_link=tk.StringVar()
        ttk.Entry(frame,textvariable=self.host_link,state='readonly').pack(fill='x')
        self.copy_button=ttk.Button(frame,text='Copiar endereço para os amigos',command=self.copy,state='disabled');self.copy_button.pack(anchor='w',pady=8)
        ttk.Separator(frame).pack(fill='x',pady=12)
        ttk.Label(frame,text='Entrar na sala de um amigo').pack(anchor='w')
        self.join_link=tk.StringVar()
        ttk.Entry(frame,textvariable=self.join_link).pack(fill='x',pady=7)
        row=ttk.Frame(frame);row.pack(fill='x')
        ttk.Button(row,text='Usar este endereço no Rose',command=self.join).pack(side='left')
        ttk.Button(row,text='Usar servidor público',command=self.public).pack(side='left',padx=8)
        ttk.Label(frame,text='Quem hospeda mantém esta janela e o computador ligados.\nAo hospedar novamente, compartilhe o novo endereço.',wraplength=590).pack(anchor='w',pady=(16,0))
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll)

    def host(self):
        self.host_link.set('');self.copy_button.configure(state='disabled');self.host_button.configure(state='disabled');self.stop_button.configure(state='normal')
        self.status.set('Preparando a sala...');self.controller.start()

    def stop(self):
        self.status.set('Encerrando a sala...');self.controller.stop()

    def copy(self):
        link=self.host_link.get()
        if link:self.root.clipboard_clear();self.root.clipboard_append(link);self.status.set('Endereço copiado. Compartilhe apenas com seus amigos.')

    def join(self):
        try:
            if self.controller.started:raise ValueError('Encerre sua hospedagem antes de entrar na sala de outro amigo.')
            if not self.join_link.get().strip():raise ValueError('Cole o endereço que o anfitrião enviou.')
            save_server_link(self.join_link.get());self.status.set('Sala escolhida. O Rose tentará conectar automaticamente; se necessário, use Tentar agora no painel.')
        except Exception as e:messagebox.showerror('Não foi possível escolher a sala',str(e),parent=self.root)

    def public(self):
        try:
            if self.controller.started:raise ValueError('Encerre a hospedagem antes de voltar ao servidor público.')
            save_server_link('');self.status.set('Servidor público selecionado. A disponibilidade depende do Rose oficial.')
        except Exception as e:messagebox.showerror('Não foi possível mudar o servidor',str(e),parent=self.root)

    def poll(self):
        try:
            while True:
                kind,value=self.controller.events.get_nowait()
                if kind=='status':self.status.set(value)
                elif kind=='ready':
                    self.host_link.set(value);self.copy_button.configure(state='normal')
                    try:save_server_link(value);self.status.set('Sala disponível! Seu Rose já usa esta sala. Copie o endereço para os amigos.')
                    except Exception as e:self.status.set('Sala disponível, mas não consegui configurar seu Rose: '+str(e))
                elif kind=='error':self.status.set(value)
                elif kind=='stopped':
                    self.host_button.configure(state='normal');self.stop_button.configure(state='disabled');self.copy_button.configure(state='disabled');self.host_link.set('')
                    if self.status.get().startswith('Encerrando'):self.status.set('Sala encerrada. Para voltar a jogar, hospede novamente ou entre na sala de um amigo.')
        except queue.Empty:pass
        if not self.closing:self.root.after(100,self.poll)

    def close(self):
        self.closing=True;self.controller.stop(wait=True);self.root.destroy()

def main():
    root=tk.Tk();SalaApp(root);root.mainloop()

if __name__=='__main__':
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='--self-test':
        from party.hosting.self_test import run
        run(sys.argv[2])
    else:
        main()


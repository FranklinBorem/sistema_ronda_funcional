const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const puppeteer = require('puppeteer');

const API_URL = 'http://127.0.0.1:5000';

let heartbeatInterval = null;

// =============================
// NORMALIZAÇÃO
// =============================

function normalizarTexto(texto = '') {
    return texto
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .trim();
}

// =============================
// FILTRO ROBUSTO
// =============================

function deveMonitorarGrupo(nomeGrupo = '') {
    const nome = normalizarTexto(nomeGrupo);

    const palavrasLocal = ['ufv', 'usina', 'fazenda', 'site'];
    const palavrasSeg = ['seguranca', 'seg', 'vigilancia', 'vigia', 'portaria', 'monitoramento'];

    const temLocal = palavrasLocal.some(p => nome.includes(p));
    const temSeg = palavrasSeg.some(p => nome.includes(p));

    return temLocal && temSeg;
}

// =============================
// LIMPAR AUTOR
// =============================

function limparAutor(id = '') {
    return id.replace('@c.us', '').replace('@lid', '').trim();
}

// =============================
// CLIENT
// =============================

const client = new Client({
    authStrategy: new LocalAuth({
        clientId:  'vigilante_ia',
        dataPath:  './.wwebjs_auth'   // pasta fixa — sessão persiste entre reinícios
    }),
    puppeteer: {
        headless: true,
        executablePath: puppeteer.executablePath(),
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-first-run',
            '--no-zygote',
            '--disable-extensions',
            '--disable-background-networking'
        ],
        timeout: 120000
    }
});

// =============================
// HEARTBEAT
// =============================

function iniciarHeartbeat() {
    if (heartbeatInterval) clearInterval(heartbeatInterval);

    heartbeatInterval = setInterval(async () => {
        try {
            await axios.post(`${API_URL}/heartbeat`, {
                timestamp: new Date().toISOString()
            }, { timeout: 5000 });

            console.log('💓 Heartbeat enviado');
        } catch {
            console.log('⚠️ API Flask offline');
        }
    }, 30000);
}

// =============================
// RESOLVER AUTOR
// =============================

async function resolverAutor(message, chat) {
    try {
        const id = message.author || message.from;
        if (!id) return 'Desconhecido';

        const numero = limparAutor(id);

        try {
            const contato = await client.getContactById(id);

            return (
                contato.pushname ||
                contato.name ||
                contato.shortName ||
                contato.number ||
                numero
            );
        } catch {}

        if (chat?.participants) {
            const p = chat.participants.find(x => x.id._serialized === id);

            if (p) {
                return (
                    p.name ||
                    p.pushname ||
                    p.shortName ||
                    numero
                );
            }
        }

        return numero;

    } catch {
        return 'Desconhecido';
    }
}

// =============================
// EVENTOS
// =============================

client.on('qr', qr => {
    console.log('\n📱 Escaneie o QR Code:\n');
    qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => {
    console.log('🔐 Autenticado com sucesso');
});

client.on('ready', async () => {
    console.log('✅ WhatsApp conectado!');

    iniciarHeartbeat();

    setTimeout(async () => {
        await sincronizarGrupos();
    }, 15000);
});

client.on('disconnected', async reason => {
    console.log('⚠️ Desconectado:', reason);
    console.log('🛑 Reinicie manualmente o sistema');
});

// =============================
// SINCRONIZAÇÃO
// =============================

async function sincronizarGrupos() {
    console.log('🔄 Sincronizando grupos...');

    const chats = await client.getChats();

    console.log(`📦 ${chats.length} chats encontrados`);

    for (const chat of chats) {
        try {
            console.log("📦 CHAT:", chat.name);

            if (!chat || !chat.isGroup) continue;

            if (!deveMonitorarGrupo(chat.name)) {
                console.log("❌ Ignorado:", chat.name);
                continue;
            }

            console.log("✅ Monitorando:", chat.name);

            const msgs = await chat.fetchMessages({ limit: 1 });

            if (!msgs.length) continue;

            const m = msgs[0];
            const autor = await resolverAutor(m, chat);

            await axios.post(`${API_URL}/mensagens`, {
                grupo: chat.name,
                autor,
                data: new Date(m.timestamp * 1000).toISOString(),
                tipo: m.type || 'chat',
                conteudo: m.body || '[mídia]'
            })
            .then(() => console.log("📤 Enviado para API"))
            .catch(err => console.log("❌ Erro API:", err.message));

        } catch (err) {
            console.log(`⚠️ Erro em ${chat?.name}:`, err.message);
        }
    }

    console.log('✅ Sincronização concluída');
}

// =============================
// NOVAS MENSAGENS
// =============================

client.on('message', async message => {
    try {
        const chat = await message.getChat();

        if (!chat || !chat.isGroup) return;
        if (!deveMonitorarGrupo(chat.name)) return;

        const autor = await resolverAutor(message, chat);

        console.log(`📩 ${chat.name}`);
        console.log(`👤 ${autor}`);

        await axios.post(`${API_URL}/mensagens`, {
            grupo: chat.name,
            autor,
            data: new Date(message.timestamp * 1000).toISOString(),
            tipo: message.type || 'chat',
            conteudo: message.hasMedia ? '[mídia]' : message.body
        })
        .catch(err => console.log("❌ Erro envio:", err.message));

    } catch (e) {
        console.log('⚠️ Erro ao processar mensagem:', e.message);
    }
});

// =============================
// ENCERRAMENTO LIMPO
// =============================

let encerrando = false;

async function encerrarLimpo(motivo = '') {
    if (encerrando) return;
    encerrando = true;

    console.log(`\n🛑 Encerrando (${motivo})...`);

    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
    }

    try {
        await client.destroy();
        console.log('✅ Cliente WhatsApp encerrado com sucesso.');
    } catch (e) {
        console.log('⚠️ Erro ao encerrar cliente:', e.message);
    }

    process.exit(0);
}

// Ctrl+C no terminal
process.on('SIGINT',  () => encerrarLimpo('SIGINT'));

// Encerramento pelo sistema (serviço Windows, etc.)
process.on('SIGTERM', () => encerrarLimpo('SIGTERM'));

// Fecha janela no Windows (fechar terminal)
process.on('SIGHUP',  () => encerrarLimpo('SIGHUP'));

// Proteção contra erros não tratados — NÃO encerra, apenas loga
process.on('unhandledRejection', err => {
    console.log('⚠️ Rejeição não tratada:', err?.message || err);
});

process.on('uncaughtException', err => {
    console.log('⚠️ Exceção não capturada:', err?.message || err);
});

// =============================
// START
// =============================

console.log('🚀 Inicializando monitor WhatsApp...');
client.initialize();
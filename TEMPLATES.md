{% extends "base.html" %}
{% block title %}{{ 'Editar' if nvr else 'Novo' }} NVR — Grupo Ronda{% endblock %}

{% block content %}
<div class="page-header">
    <h1>{{ 'Editar NVR' if nvr else 'Novo NVR' }}</h1>
    <a href="{{ url_for('conferencia.nvrs_listar') }}" class="btn btn-primary btn-sm">← Voltar</a>
</div>

<style>
    .form-section {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .form-section-title {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: .12em;
        color: var(--text-muted);
        text-transform: uppercase;
        margin-bottom: 1.25rem;
        padding-bottom: .75rem;
        border-bottom: 1px solid var(--border);
    }
    .preset-row {
        display: grid;
        grid-template-columns: 70px 1fr 34px;
        gap: 8px;
        align-items: center;
        margin-bottom: 8px;
    }
    .preset-row input {
        background: rgba(255,255,255,0.04);
        border: 1px solid var(--border);
        border-radius: 6px;
        color: var(--text-main);
        padding: 8px 10px;
        font-size: 13px;
        font-family: 'DM Sans', sans-serif;
        outline: none;
    }
    .preset-row input:focus {
        border-color: rgba(245,196,0,.5);
    }
    .preset-del {
        width: 34px;
        height: 34px;
        border-radius: 6px;
        border: 1px solid var(--border);
        background: rgba(239,68,68,.08);
        color: var(--text-muted);
        cursor: pointer;
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all .15s;
    }
    .preset-del:hover {
        border-color: rgba(239,68,68,.4);
        color: #f87171;
    }
    .add-preset {
        font-size: 11px;
        font-weight: 700;
        color: var(--gold);
        background: var(--gold-glow);
        border: 1px solid var(--gold-border);
        padding: 5px 12px;
        border-radius: 5px;
        cursor: pointer;
        transition: background .15s;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }
    .add-preset:hover {
        background: rgba(245,196,0,.2);
    }
</style>

<form method="POST" id="form-nvr">
<div style="display:grid; grid-template-columns:1fr 1fr; gap:1.5rem;">

    <!-- COLUNA ESQUERDA: identificação e canais -->
    <div>
        <div class="form-section">
            <div class="form-section-title">Identificação</div>

            <div class="form-group">
                <label>ID do NVR <span style="color:var(--text-muted); font-size:11px;">(único, sem espaços)</span></label>
                <input type="text" name="nvr_id" value="{{ nvr.nvr_id if nvr else '' }}"
                       placeholder="ex: altair_sp_dome_01" required
                       {% if nvr %}readonly style="opacity:.6; cursor:not-allowed;"{% endif %}>
            </div>

            <div class="form-group">
                <label>Nome / Identificação</label>
                <input type="text" name="nome" value="{{ nvr.nome if nvr else '' }}"
                       placeholder="UFV Altair - Dome 01" required>
            </div>

            <div class="form-group">
                <label>Site / Usina</label>
                <input type="text" name="site" value="{{ nvr.site if nvr else '' }}"
                       placeholder="Altair - SP">
            </div>

            <div class="form-group">
                <label>Endereço IP</label>
                <input type="text" name="ip" value="{{ nvr.ip if nvr else '' }}"
                       placeholder="10.38.10.202" required>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
                <div class="form-group">
                    <label>Usuário</label>
                    <input type="text" name="usuario" value="{{ nvr.usuario if nvr else 'admin' }}" required>
                </div>
                <div class="form-group">
                    <label>Senha</label>
                    <input type="password" name="senha" value="{{ nvr.senha if nvr else '' }}"
                           placeholder="{% if nvr %}deixe em branco para manter{% else %}senha{% endif %}">
                    {% if nvr %}
                    <small>Deixe em branco para manter a senha atual.</small>
                    {% endif %}
                </div>
            </div>
        </div>

        <div class="form-section">
            <div class="form-section-title">Configuração de Canais</div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
                <div class="form-group">
                    <label>Canal PTZ</label>
                    <input type="number" name="ptz_channel" value="{{ nvr.ptz_channel if nvr else 1 }}" min="1" max="64" required>
                </div>
                <div class="form-group">
                    <label>Canal Snapshot</label>
                    <input type="text" name="snapshot_channel" value="{{ nvr.snapshot_channel if nvr else '501' }}" required>
                </div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:0.5rem;">
                <div class="form-group">
                    <label>Espera após PTZ (s)</label>
                    <input type="number" name="tempo_espera" value="{{ nvr.tempo_espera if nvr else 5 }}" min="1" max="30" required>
                </div>
                <div class="form-group">
                    <label>Timeout (s)</label>
                    <input type="number" name="timeout" value="{{ nvr.timeout if nvr else 10 }}" min="3" max="60" required>
                </div>
            </div>

            <div class="form-group" style="margin-top:1rem;">
                <label style="display:flex; align-items:center; gap:10px; cursor:pointer; text-transform:none; font-size:13px; font-weight:500;">
                    <input type="checkbox" name="ativo" value="1" {% if not nvr or nvr.ativo %}checked{% endif %}
                           style="width:16px; height:16px; accent-color:var(--gold);">
                    <span>NVR ativo (incluir no monitoramento)</span>
                </label>
            </div>
        </div>
    </div>

    <!-- COLUNA DIREITA: presets -->
    <div>
        <div class="form-section" style="height: 100%;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem; padding-bottom:.75rem; border-bottom:1px solid var(--border);">
                <div class="form-section-title" style="margin-bottom:0; padding-bottom:0; border-bottom:none;">Presets PTZ</div>
                <button type="button" onclick="adicionarPreset()" class="add-preset">+ Adicionar</button>
            </div>

            <div style="font-size:12px; color:var(--text-muted); margin-bottom:1rem;">
                Cada preset é uma posição salva na câmera. O número deve corresponder ao preset configurado no PTZ.
            </div>

            <div id="lista-presets" style="display:flex; flex-direction:column; gap:8px;">
                {% if presets %}
                    {% for p in presets %}
                    <div class="preset-row">
                        <input type="number" name="preset_num[]" value="{{ p.numero }}" min="1" max="256" placeholder="Nº" style="text-align:center;">
                        <input type="text" name="preset_nome[]" value="{{ p.nome }}" placeholder="Ex: Portao_Norte">
                        <button type="button" onclick="this.closest('.preset-row').remove()" class="preset-del">×</button>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="preset-row">
                        <input type="number" name="preset_num[]" min="1" max="256" placeholder="Nº" style="text-align:center;">
                        <input type="text" name="preset_nome[]" placeholder="Ex: Portao_Norte">
                        <button type="button" onclick="this.closest('.preset-row').remove()" class="preset-del">×</button>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<!-- BOTÕES -->
<div style="display:flex; justify-content:space-between; align-items:center; margin-top:1.5rem;">
    {% if nvr %}
    <form method="POST" action="{{ url_for('conferencia.nvrs_excluir', nvr_id=nvr.nvr_id) }}"
          onsubmit="return confirm('Excluir {{ nvr.nome }}? Esta ação não pode ser desfeita.')">
        <button type="submit" class="btn btn-danger btn-sm">Excluir NVR</button>
    </form>
    {% else %}
    <div></div>
    {% endif %}
    <div style="display:flex; gap:10px;">
        <a href="{{ url_for('conferencia.nvrs_listar') }}" class="btn btn-secondary">Cancelar</a>
        <button type="submit" class="btn btn-success">Salvar</button>
    </div>
</div>
</form>

<script>
function adicionarPreset() {
    const container = document.getElementById('lista-presets');
    const row = document.createElement('div');
    row.className = 'preset-row';
    row.innerHTML = `
        <input type="number" name="preset_num[]" min="1" max="256" placeholder="Nº" style="text-align:center;">
        <input type="text" name="preset_nome[]" placeholder="Ex: Portao_Norte">
        <button type="button" onclick="this.closest('.preset-row').remove()" class="preset-del">×</button>
    `;
    container.appendChild(row);
    row.querySelector('input[type=number]').focus();
}
</script>
{% endblock %}

{% extends "base.html" %}
{% block title %}Importar NVRs — Grupo Ronda{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Importar NVRs em Lote</h1>
    <a href="{{ url_for('conferencia.nvrs_listar') }}" class="btn btn-primary btn-sm">← Voltar</a>
</div>

<style>
    .import-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
        margin-bottom: 1.5rem;
    }
    .import-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.5rem;
    }
    .import-card-title {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: .12em;
        color: var(--text-muted);
        text-transform: uppercase;
        margin-bottom: 1.25rem;
        padding-bottom: .75rem;
        border-bottom: 1px solid var(--border);
    }
    .upload-area {
        border: 2px dashed var(--border);
        border-radius: 10px;
        padding: 3rem 2rem;
        text-align: center;
        cursor: pointer;
        transition: all .2s;
        position: relative;
    }
    .upload-area:hover,
    .upload-area.drag-over {
        border-color: var(--gold-border);
        background: var(--gold-soft);
    }
    .upload-area input[type=file] {
        position: absolute;
        inset: 0;
        opacity: 0;
        cursor: pointer;
        width: 100%;
        height: 100%;
    }
    .upload-icon {
        font-size: 2.5rem;
        margin-bottom: .75rem;
        display: block;
    }
    .upload-label {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-main);
        display: block;
        margin-bottom: .5rem;
    }
    .upload-hint {
        font-size: 11px;
        color: var(--text-muted);
    }
    .selected-file {
        display: none;
        margin-top: 1rem;
        background: var(--gold-soft);
        border: 1px solid var(--gold-border);
        border-radius: 6px;
        padding: 10px 14px;
        font-size: 12px;
        color: var(--gold);
        align-items: center;
        gap: 8px;
    }
    .col-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
    }
    .col-table th {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: .1em;
        color: var(--text-muted);
        text-transform: uppercase;
        text-align: left;
        padding: 6px 10px;
        border-bottom: 1px solid var(--border);
    }
    .col-table td {
        padding: 8px 10px;
        border-bottom: 1px solid rgba(255,255,255,0.03);
        color: var(--text-main);
        vertical-align: top;
    }
    .col-table td:first-child {
        font-family: monospace;
        font-size: 11px;
        color: var(--gold);
    }
    .col-table tr:last-child td {
        border-bottom: none;
    }
    .badge-obrig {
        display: inline-block;
        font-size: 9px;
        font-weight: 700;
        color: var(--red);
        background: var(--red-soft);
        border-radius: 4px;
        padding: 1px 5px;
        margin-left: 4px;
        text-transform: uppercase;
    }
    .badge-padrao {
        display: inline-block;
        font-size: 9px;
        font-weight: 700;
        color: var(--text-muted);
        background: rgba(255,255,255,0.05);
        border-radius: 4px;
        padding: 1px 5px;
        margin-left: 4px;
        text-transform: uppercase;
    }
    .csv-preview {
        background: rgba(0,0,0,0.3);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1rem;
        font-family: monospace;
        font-size: 11px;
        color: var(--text-muted);
        overflow-x: auto;
        line-height: 1.8;
        white-space: pre;
    }
    .csv-preview .h { color: var(--gold); font-weight: 700; }
    .csv-preview .v { color: #a0e0b0; }
    .rules-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    .rules-list li {
        font-size: 12px;
        color: var(--text-muted);
        padding: 5px 0;
        border-bottom: 1px solid rgba(255,255,255,0.03);
        display: flex;
        gap: 8px;
        align-items: flex-start;
    }
    .rules-list li:last-child { border-bottom: none; }
    .rules-list li::before {
        content: "·";
        color: var(--gold);
        font-size: 16px;
        line-height: 1;
        flex-shrink: 0;
    }
    .submit-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 1.5rem;
    }
</style>

<!-- ALERTAS FLASH -->
{% with messages = get_flashed_messages(with_categories=true) %}
{% if messages %}
<div style="margin-bottom:1rem;">
    {% for cat, msg in messages %}
    <div class="alert alert-{{ cat }}" style="margin-bottom:.5rem;">{{ msg }}</div>
    {% endfor %}
</div>
{% endif %}
{% endwith %}

<div class="import-grid">

    <!-- COLUNA ESQUERDA: upload -->
    <div>
        <div class="import-card">
            <div class="import-card-title">Arquivo CSV</div>

            <form method="POST" enctype="multipart/form-data" id="form-import">
                <div class="upload-area" id="drop-area">
                    <input type="file" name="arquivo" id="arquivo-input"
                           accept=".csv,.txt" onchange="onFileSelect(this)">
                    <span class="upload-icon">📂</span>
                    <span class="upload-label">Arraste o CSV aqui ou clique para selecionar</span>
                    <span class="upload-hint">Formatos: .csv · Separador: ; ou ,<br>Encoding: UTF-8 ou Latin-1</span>
                </div>

                <div class="selected-file" id="selected-file">
                    <span>📄</span>
                    <span id="selected-file-name"></span>
                </div>

                <div class="submit-row">
                    <a href="{{ url_for('conferencia.nvrs_importar_modelo') }}"
                       class="btn btn-secondary btn-sm">
                        ⬇ Baixar CSV modelo
                    </a>
                    <button type="submit" class="btn btn-success" id="btn-submit" disabled>
                        Importar NVRs
                    </button>
                </div>
            </form>
        </div>

        <!-- Regras -->
        <div class="import-card" style="margin-top:1rem;">
            <div class="import-card-title">Regras de importação</div>
            <ul class="rules-list">
                <li>Linhas com <code>nvr_id</code> já cadastrado são <strong>ignoradas</strong> — não sobrescreve dados existentes.</li>
                <li>Linhas com <code>nvr_id</code> ou <code>ip</code> vazios são descartadas com aviso.</li>
                <li>Campos <code>porta</code>, <code>usuario</code> e <code>ativo</code> têm valores padrão e são opcionais.</li>
                <li>Valores de <code>use_https</code> e <code>ativo</code>: use <code>1</code>, <code>sim</code>, <code>true</code> para ativar; qualquer outro valor (inclusive vazio) desativa.</li>
                <li>A planilha pode ser exportada do Excel como <em>CSV (separado por vírgulas)</em> ou <em>CSV UTF-8 (separado por ponto e vírgula)</em>.</li>
                <li>Número máximo recomendado por importação: <strong>200 NVRs</strong>.</li>
            </ul>
        </div>
    </div>

    <!-- COLUNA DIREITA: estrutura do CSV -->
    <div>
        <div class="import-card">
            <div class="import-card-title">Estrutura do CSV</div>

            <table class="col-table">
                <thead>
                    <tr>
                        <th>Coluna</th>
                        <th>Descrição</th>
                        <th>Padrão</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>nvr_id <span class="badge-obrig">obrigatório</span></td>
                        <td>Identificador único (sem espaços). Ex: <code>nvr_altair_01</code></td>
                        <td>—</td>
                    </tr>
                    <tr>
                        <td>ip <span class="badge-obrig">obrigatório</span></td>
                        <td>Endereço IP do dispositivo. Ex: <code>10.38.10.202</code></td>
                        <td>—</td>
                    </tr>
                    <tr>
                        <td>nome</td>
                        <td>Nome de exibição. Ex: <code>UFV Altair - NVR 01</code></td>
                        <td><span class="badge-padrao">= nvr_id</span></td>
                    </tr>
                    <tr>
                        <td>site</td>
                        <td>Usina / localidade. Ex: <code>Altair SP</code></td>
                        <td><span class="badge-padrao">vazio</span></td>
                    </tr>
                    <tr>
                        <td>porta</td>
                        <td>Porta HTTP do dispositivo</td>
                        <td><span class="badge-padrao">80</span></td>
                    </tr>
                    <tr>
                        <td>usuario</td>
                        <td>Usuário de acesso ao NVR/câmera</td>
                        <td><span class="badge-padrao">admin</span></td>
                    </tr>
                    <tr>
                        <td>senha</td>
                        <td>Senha de acesso</td>
                        <td><span class="badge-padrao">vazio</span></td>
                    </tr>
                    <tr>
                        <td>use_https</td>
                        <td>Usar HTTPS? (<code>1</code> = sim)</td>
                        <td><span class="badge-padrao">0</span></td>
                    </tr>
                    <tr>
                        <td>ativo</td>
                        <td>Incluir no monitoramento? (<code>1</code> = sim)</td>
                        <td><span class="badge-padrao">1</span></td>
                    </tr>
                </tbody>
            </table>

            <div style="margin-top:1.25rem;">
                <div class="import-card-title" style="margin-top:0;">Exemplo de conteúdo</div>
                <div class="csv-preview"><span class="h">nvr_id;nome;site;ip;porta;usuario;senha;use_https;ativo</span>
<span class="v">nvr_altair_01;UFV Altair - NVR 01;Altair SP;10.38.10.202;80;admin;senha123;0;1</span>
<span class="v">nvr_altair_02;UFV Altair - NVR 02;Altair SP;10.38.10.203;80;admin;senha123;0;1</span>
<span class="v">nvr_sp_dome_01;SP Dome 01;São Paulo;192.168.1.100;8080;admin;outrasenha;0;1</span></div>
            </div>
        </div>
    </div>
</div>

<script>
// Drag & drop visual
const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('arquivo-input');
const btnSubmit = document.getElementById('btn-submit');
const selectedFile = document.getElementById('selected-file');
const selectedFileName = document.getElementById('selected-file-name');

['dragenter','dragover'].forEach(evt => {
    dropArea.addEventListener(evt, e => { e.preventDefault(); dropArea.classList.add('drag-over'); });
});
['dragleave','drop'].forEach(evt => {
    dropArea.addEventListener(evt, e => { e.preventDefault(); dropArea.classList.remove('drag-over'); });
});
dropArea.addEventListener('drop', e => {
    fileInput.files = e.dataTransfer.files;
    onFileSelect(fileInput);
});

function onFileSelect(input) {
    const file = input.files[0];
    if (!file) return;
    selectedFileName.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    selectedFile.style.display = 'flex';
    btnSubmit.disabled = false;
    btnSubmit.textContent = `Importar "${file.name}"`;
}
</script>
{% endblock %}

{% extends "base.html" %}
{% block title %}NVRs Monitorados — Grupo Ronda{% endblock %}

{% block content %}
<div class="page-header">
    <h1>NVRs Monitorados</h1>
    <div style="display:flex; gap:8px;">
        <a href="{{ url_for('conferencia.nvrs_importar') }}" class="btn btn-secondary btn-sm">↑ Importar CSV</a>
        <a href="{{ url_for('conferencia.nvrs_novo') }}" class="btn btn-success">+ Adicionar NVR</a>
    </div>
</div>

{% with messages = get_flashed_messages(with_categories=true) %}
{% if messages %}
<div style="margin-bottom:1rem;">
    {% for cat, msg in messages %}
    <div class="alert alert-{{ cat }}" style="margin-bottom:.5rem;">{{ msg }}</div>
    {% endfor %}
</div>
{% endif %}
{% endwith %}

{% if migrados is defined and migrados > 0 %}
<div class="alert alert-info">
    {{ migrados }} PTZ(s) importadas automaticamente da planilha.
</div>
{% endif %}

{% if not nvrs %}
<div class="card" style="text-align: center; padding: 3rem;">
    <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 1rem;">Nenhum NVR cadastrado ainda.</div>
    <div style="display:flex; gap:10px; justify-content:center;">
        <a href="{{ url_for('conferencia.nvrs_importar') }}" class="btn btn-secondary">↑ Importar CSV em lote</a>
        <a href="{{ url_for('conferencia.nvrs_novo') }}" class="btn btn-success">+ Cadastrar manualmente</a>
    </div>
</div>
{% else %}

<div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden;">

    <!-- Cabeçalho da tabela -->
    <div style="display:grid; grid-template-columns:160px 1fr 120px 80px 100px 120px;
                background: rgba(245,196,0,0.04); padding:10px 16px; gap:12px;
                border-bottom: 1px solid var(--border);">
        <div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:var(--text-muted);">ID</div>
        <div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:var(--text-muted);">NOME / IP</div>
        <div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:var(--text-muted);">PORTA</div>
        <div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:var(--text-muted);">HTTPS</div>
        <div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:var(--text-muted);">STATUS</div>
        <div></div>
    </div>

    {% for nvr in nvrs %}
    <div style="display:grid; grid-template-columns:160px 1fr 120px 80px 100px 120px;
                padding:14px 16px; gap:12px; align-items:center;
                border-bottom: 1px solid rgba(255,255,255,0.04);
                transition: background 0.15s;
                {% if not nvr.ativo %}opacity:.5;{% endif %}"
         onmouseover="this.style.background='rgba(245,196,0,0.03)'"
         onmouseout="this.style.background='transparent'">

        <div style="font-family:monospace; font-size:11px; color:var(--text-muted); word-break:break-all;">
            {{ nvr.nvr_id }}
        </div>

        <div>
            <div style="font-size:13px; font-weight:700; color:#fff;">{{ nvr.nome }}</div>
            <div style="font-size:11px; color:var(--text-muted); margin-top:2px; font-family:monospace;">
                {{ nvr.ip }}
            </div>
            {% if nvr.site %}
            <div style="font-size:10px; color:var(--text-dim); margin-top:2px;">🏭 {{ nvr.site }}</div>
            {% endif %}
        </div>

        <div style="font-size:12px; color:var(--text-muted); font-family:monospace;">
            :{{ nvr.porta }}
        </div>

        <div>
            {% if nvr.use_https %}
            <span style="font-size:10px; font-weight:700; color:var(--green);
                         background:var(--green-soft); border-radius:4px; padding:2px 6px;">HTTPS</span>
            {% else %}
            <span style="font-size:10px; color:var(--text-dim);">HTTP</span>
            {% endif %}
        </div>

        <div>
            {% if nvr.ativo %}
            <span class="badge badge-success">ATIVO</span>
            {% else %}
            <span class="badge badge-secondary">INATIVO</span>
            {% endif %}
        </div>

        <div style="display:flex; gap:6px;">
            <a href="{{ url_for('conferencia.nvrs_editar', nvr_id=nvr.nvr_id) }}"
               class="btn btn-primary btn-sm">Editar</a>
            <form method="POST" action="{{ url_for('conferencia.nvrs_toggle', nvr_id=nvr.nvr_id) }}"
                  style="margin:0;">
                <button type="submit" class="btn btn-secondary btn-sm">
                    {{ 'Desativar' if nvr.ativo else 'Ativar' }}
                </button>
            </form>
        </div>
    </div>
    {% endfor %}

</div>

<div style="margin-top:.75rem; font-size:11px; color:var(--text-dim);">
    {{ nvrs|length }} NVR(s) cadastrado(s) —
    {{ nvrs|selectattr('ativo')|list|length }} ativo(s)
</div>

{% endif %}
{% endblock %}

{% extends "base.html" %}
{% block title %}Conferência de Câmeras — Grupo Ronda{% endblock %}

{% block extra_css %}
<style>
  /* ── Tokens locais (herdam do base.html) ── */
  .conf-wrap {
    /* o base.html já envolve em .container com max-width:1160px e padding */
  }

  /* ── Cabeçalho ── */
  .conf-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .conf-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 22px;
    font-weight: 800;
    color: var(--text);
    text-transform: uppercase;
    letter-spacing: .06em;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .conf-title::before {
    content: '';
    width: 3px; height: 20px;
    background: var(--gold);
    border-radius: 2px;
    display: inline-block;
  }
  .conf-subtitle { font-size: 12px; color: var(--text-3); margin-top: 3px; }

  /* ── Botões ── */
  .btn-poll {
    background: var(--gold);
    color: #111;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 700;
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    letter-spacing: .04em;
    transition: all .15s;
    white-space: nowrap;
  }
  .btn-poll:hover { background: #ffd633; box-shadow: 0 4px 16px rgba(245,196,0,.3); }
  .btn-poll:disabled { opacity: .45; cursor: not-allowed; box-shadow: none; }
  .btn-poll .spin {
    width: 13px; height: 13px;
    border: 2px solid #0006;
    border-top-color: #000;
    border-radius: 50%;
    animation: rg-spin .6s linear infinite;
    display: none;
  }
  .btn-poll.loading .spin { display: inline-block; }
  @keyframes rg-spin { to { transform: rotate(360deg); } }

  .btn-logs {
    background: transparent;
    color: var(--text-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    cursor: pointer;
    transition: all .15s;
  }
  .btn-logs:hover { background: var(--bg-3); border-color: rgba(255,255,255,.15); color: var(--text); }

  /* ── Summary cards ── */
  .summary-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: .65rem;
    margin-bottom: 1.5rem;
  }
  .s-card {
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: .9rem 1rem;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .s-card::before { content:''; position:absolute; top:0;left:0;right:0; height:2px; }
  .s-card.c-gold::before  { background: var(--gold); }
  .s-card.c-green::before { background: var(--green); }
  .s-card.c-red::before   { background: var(--red); }
  .s-card.c-orange::before{ background: var(--orange); }
  .s-num {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 32px; font-weight: 800; line-height: 1;
    color: var(--text);
  }
  .s-num.ok     { color: var(--green); }
  .s-num.warn   { color: var(--orange); }
  .s-num.err    { color: var(--red); }
  .s-lbl {
    font-size: 10px; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: var(--text-3); margin-top: 4px;
  }

  /* ── Timestamp ── */
  .ts-line {
    font-size: 11px; color: var(--text-3); font-family: monospace;
    margin-bottom: 1rem;
    display: flex; align-items: center; gap: .5rem;
  }
  .ts-line span { color: var(--text-2); }

  /* ── NVR cards ── */
  .nvr-stack { display: flex; flex-direction: column; gap: 1rem; }

  .nvr-card {
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    transition: border-color .2s;
  }
  .nvr-card.h-ok   { border-left: 3px solid var(--green); }
  .nvr-card.h-warn { border-left: 3px solid var(--orange); }
  .nvr-card.h-err  { border-left: 3px solid var(--red); }

  .nvr-head {
    display: flex; align-items: center;
    padding: .85rem 1.1rem; gap: .85rem;
    cursor: pointer; user-select: none;
    border-bottom: 1px solid transparent;
    transition: background .12s;
  }
  .nvr-head:hover { background: var(--bg-3); }
  .nvr-card.open .nvr-head { border-bottom-color: var(--border); }

  .nvr-dot {
    width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0;
  }
  .nvr-dot.ok   { background: var(--green);  box-shadow: 0 0 7px var(--green); }
  .nvr-dot.warn { background: var(--orange); box-shadow: 0 0 7px var(--orange); }
  .nvr-dot.err  { background: var(--red);    box-shadow: 0 0 7px var(--red); }

  .nvr-names { flex: 1; min-width: 0; }
  .nvr-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 15px; font-weight: 700;
    color: var(--text); letter-spacing: .03em;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .nvr-meta { font-size: 11px; color: var(--text-3); font-family: monospace; margin-top: 1px; }

  .nvr-counts {
    display: flex; gap: 1.2rem; flex-shrink: 0;
  }
  .nvr-cnt { display: flex; flex-direction: column; align-items: center; }
  .nvr-cnt .n { font-family: 'Barlow Condensed', sans-serif; font-size: 20px; font-weight: 800; line-height: 1; }
  .nvr-cnt .n.ok  { color: var(--green); }
  .nvr-cnt .n.err { color: var(--red); }
  .nvr-cnt .l { font-size: 9px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: var(--text-3); margin-top: 1px; }

  .nvr-ms { font-size: 10px; color: var(--text-3); font-family: monospace; flex-shrink: 0; text-align: right; }

  .nvr-arrow { color: var(--text-3); font-size: 11px; transition: transform .2s; flex-shrink: 0; }
  .nvr-card.open .nvr-arrow { transform: rotate(90deg); }

  /* ── NVR body ── */
  .nvr-body { display: none; padding: 1rem 1.1rem; }
  .nvr-card.open .nvr-body { display: block; }

  /* ── Device info strip ── */
  .dev-strip {
    display: flex; flex-wrap: wrap; gap: .5rem;
    margin-bottom: .9rem;
    padding-bottom: .9rem;
    border-bottom: 1px solid var(--border);
  }
  .dev-chip {
    font-size: 11px; font-family: monospace;
    color: var(--text-3);
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 3px 8px;
  }
  .dev-chip strong { color: var(--text-2); }

  /* ── HDD strip ── */
  .hdd-row { display: flex; flex-wrap: wrap; gap: .6rem; margin-bottom: .9rem; }
  .hdd-chip {
    background: var(--bg-3); border: 1px solid var(--border);
    border-radius: 7px; padding: .4rem .8rem;
    font-size: 11px; display: flex; align-items: center; gap: .5rem;
  }
  .h-dot { width: 7px; height: 7px; border-radius: 50%; }
  .h-dot.ok   { background: var(--green); }
  .h-dot.warn { background: var(--orange); }
  .h-dot.err  { background: var(--red); }
  .h-bar {
    height: 4px; width: 56px;
    background: var(--border); border-radius: 2px; overflow: hidden;
  }
  .h-fill { height: 100%; border-radius: 2px; background: var(--green); transition: width .4s; }
  .h-fill.warn { background: var(--orange); }
  .h-fill.crit { background: var(--red); }

  /* ── Camera table ── */
  .cam-tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
  .cam-tbl th {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .09em; color: var(--text-3);
    padding: .4rem .65rem; text-align: left;
    border-bottom: 1px solid var(--border);
  }
  .cam-tbl td {
    padding: .5rem .65rem; border-bottom: 1px solid var(--border);
    color: var(--text-2); vertical-align: middle;
  }
  .cam-tbl tr:last-child td { border-bottom: none; }
  .cam-tbl tr:hover td { background: var(--bg-3); color: var(--text); }

  .pill {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 2px 8px; border-radius: 20px;
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
  }
  .pill.online  { background: var(--green-soft);  color: var(--green);  border: 1px solid rgba(34,197,94,.3); }
  .pill.offline { background: var(--red-soft);    color: var(--red);    border: 1px solid rgba(232,64,87,.3); }
  .pill.idle    { background: var(--bg-4, #222); color: var(--text-3); border: 1px solid var(--border); }

  .signal-ok  { color: var(--green); font-size: 11px; }
  .signal-err { color: var(--red);   font-size: 11px; }
  .rec-on  { color: var(--red);    font-size: 10px; font-weight: 700; font-family: monospace; letter-spacing: .06em; }
  .rec-off { color: var(--text-3); font-size: 10px; }
  .mono    { font-family: monospace; color: var(--text-3); }

  /* ── Error / unreachable ── */
  .nvr-err-body {
    padding: .8rem 1.1rem 1rem;
    font-size: 12px; font-family: monospace; color: var(--red);
  }

  /* ── Empty / states ── */
  .state-empty {
    text-align: center; padding: 3.5rem 1rem; color: var(--text-3); font-size: 13px;
  }
  .state-empty .ico { font-size: 2.8rem; margin-bottom: .6rem; }

  /* ── Log drawer ── */
  .log-drawer {
    display: none;
    background: var(--bg-2); border: 1px solid var(--border);
    border-radius: 10px; margin-top: 1rem;
    overflow: hidden;
  }
  .log-drawer.open { display: block; }
  .log-drawer-head {
    background: var(--bg-3); padding: .7rem 1rem;
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid var(--border);
  }
  .log-drawer-title {
    font-family: 'Barlow Condensed', sans-serif; font-size: 13px;
    font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--text);
  }
  .log-list {
    max-height: 320px; overflow-y: auto;
    font-family: monospace; font-size: 11px;
  }
  .log-entry {
    display: grid; grid-template-columns: 140px 70px 1fr;
    gap: .5rem; padding: .35rem 1rem;
    border-bottom: 1px solid var(--border);
    align-items: baseline;
  }
  .log-entry:last-child { border-bottom: none; }
  .log-ts    { color: var(--text-3); }
  .log-lvl   { font-weight: 700; font-size: 10px; text-transform: uppercase; }
  .log-lvl.INFO    { color: var(--green); }
  .log-lvl.WARNING { color: var(--orange); }
  .log-lvl.ERROR   { color: var(--red); }
  .log-lvl.DEBUG   { color: var(--text-3); }
  .log-msg   { color: var(--text-2); }
  .log-detail { color: var(--text-3); font-size: 10px; }
</style>
{% endblock %}

{% block content %}

<!-- Cabeçalho -->
<div class="conf-topbar">
  <div>
    <div class="conf-title">Conferência de Câmeras</div>
    <div class="conf-subtitle">Status em tempo real via Hikvision ISAPI · Digest Auth</div>
  </div>
  <div style="display:flex;gap:.5rem;align-items:center;">
    <a href="{{ url_for('conferencia.nvrs_listar') }}" class="btn-logs">🗄 Gerenciar NVRs</a>
    <a href="{{ url_for('conferencia.relatorio') }}" class="btn-logs">📊 Relatório</a>
    <button class="btn-logs" id="btnLogs" onclick="toggleLogs()">⚠ Eventos</button>
    <button class="btn-poll" id="btnPoll" onclick="carregarStatus()">
      <span class="spin" id="pollSpin"></span>
      <span id="pollLbl">↺ Atualizar</span>
    </button>
  </div>
</div>

<!-- Resumo -->
<div class="summary-row">
  <div class="s-card c-gold"><div class="s-num" id="sNvrs">–</div><div class="s-lbl">NVRs</div></div>
  <div class="s-card c-green"><div class="s-num ok" id="sOk">–</div><div class="s-lbl">NVRs OK</div></div>
  <div class="s-card c-orange"><div class="s-num warn" id="sWarn">–</div><div class="s-lbl">Atenção</div></div>
  <div class="s-card c-red"><div class="s-num err" id="sErr">–</div><div class="s-lbl">Inacessíveis</div></div>
  <div class="s-card c-gold"><div class="s-num" id="sCTotal">–</div><div class="s-lbl">Câmeras</div></div>
  <div class="s-card c-green"><div class="s-num ok" id="sCOn">–</div><div class="s-lbl">Online</div></div>
  <div class="s-card c-red"><div class="s-num err" id="sCOff">–</div><div class="s-lbl">Offline</div></div>
</div>

<!-- Timestamp -->
<div class="ts-line" id="tsLine">Aguardando primeira consulta…</div>

<!-- Log drawer -->
<div class="log-drawer" id="logDrawer">
  <div class="log-drawer-head">
    <span class="log-drawer-title">⚠ Eventos de Monitoramento</span>
    <div style="display:flex;gap:.5rem;align-items:center;">
      <label style="font-size:11px;color:var(--text-3);display:flex;align-items:center;gap:5px;cursor:pointer;">
        <input type="checkbox" id="chkTodos" onchange="carregarLogs()"
               style="accent-color:var(--gold);width:13px;height:13px;">
        Mostrar resolvidos
      </label>
      <button class="btn-logs" onclick="carregarLogs()" style="font-size:11px;padding:4px 10px;">↺ Atualizar</button>
      <button class="btn-logs" onclick="toggleLogs()" style="font-size:11px;padding:4px 10px;">✕</button>
    </div>
  </div>
  <div class="log-list" id="logList">
    <div style="padding:1.5rem;text-align:center;color:var(--text-3);font-size:12px;">Nenhum log ainda.</div>
  </div>
</div>

<!-- Lista de NVRs -->
<div class="nvr-stack" id="nvrStack">
  <div class="state-empty">
    <div class="ico">🎥</div>
    Clique em <strong style="color:var(--gold);">Atualizar</strong> para consultar os NVRs
  </div>
</div>

{% endblock %}

{% block extra_js %}
<script>
const POLL_URL     = "{{ url_for('conferencia.api_status') }}";
const EVENTOS_URL  = "{{ url_for('conferencia.api_eventos') }}";

// ── Loading state ──────────────────────────────────────
function setLoading(on) {
  const btn = document.getElementById('btnPoll');
  const sp  = document.getElementById('pollSpin');
  const lbl = document.getElementById('pollLbl');
  btn.disabled = on;
  btn.classList.toggle('loading', on);
  sp.style.display  = on ? 'inline-block' : 'none';
  lbl.textContent   = on ? 'Consultando…' : '↺ Atualizar';
}

// ── Helpers de classe ──────────────────────────────────
function hClass(health) {
  if (health === 'OK') return 'ok';
  if (health === 'ATENÇÃO') return 'warn';
  return 'err';
}
function hddDot(s) { return s === 0 ? 'ok' : (s === 1 ? 'warn' : 'err'); }
function hddBar(p) { return p > 90 ? 'crit' : (p > 75 ? 'warn' : ''); }

// ── Renderização de câmeras ────────────────────────────
function pillCam(c) {
  if (!c.online) return `<span class="pill offline">● Offline</span>`;
  if (c.raw_status === 'idle') return `<span class="pill idle">Idle</span>`;
  return `<span class="pill online">● Online</span>`;
}

function renderCams(cams) {
  if (!cams || cams.length === 0)
    return `<p style="color:var(--text-3);font-size:12px;padding:.5rem 0;">Nenhum canal.</p>`;

  const rows = cams.map(c => {
    const sig = c.signal_ok
      ? `<span class="signal-ok">● Normal</span>`
      : `<span class="signal-err">● Perda</span>`;
    const rec = c.recording
      ? `<span class="rec-on">● REC</span>`
      : `<span class="rec-off">○ –</span>`;
    const recEx = c.recording
      ? (['OK','Exc HD','Offline','Outro'][c.record_status] || '?')
      : '';
    return `<tr>
      <td class="mono">${c.id}</td>
      <td><strong style="color:var(--text)">${c.name}</strong></td>
      <td>${pillCam(c)}</td>
      <td>${sig}</td>
      <td>${rec} <span style="font-size:10px;color:var(--text-3)">${recEx}</span></td>
      <td class="mono">${c.bit_rate_kbps ? c.bit_rate_kbps + ' Kbps' : '–'}</td>
      <td class="mono">${c.ip || '–'}</td>
      <td style="font-size:11px;color:var(--text-3)">${c.model || '–'}</td>
    </tr>`;
  }).join('');

  return `<table class="cam-tbl">
    <thead><tr>
      <th>Canal</th><th>Nome</th><th>Status</th><th>Sinal</th>
      <th>Gravação</th><th>Bitrate</th><th>IP</th><th>Modelo</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

// ── Renderização de HDDs ───────────────────────────────
function renderHdds(hdds) {
  if (!hdds || hdds.length === 0) return '';
  const chips = hdds.map(h => {
    const capGB  = (h.capacity_mb  / 1024).toFixed(0);
    const freeGB = (h.free_space_mb / 1024).toFixed(0);
    return `<div class="hdd-chip">
      <span class="h-dot ${hddDot(h.status)}"></span>
      <span style="color:var(--text-2)">HD${h.id} · <strong>${h.status_label}</strong></span>
      <div class="h-bar"><div class="h-fill ${hddBar(h.usage_pct)}" style="width:${h.usage_pct}%"></div></div>
      <span style="color:var(--text-3);font-size:10px">${h.usage_pct}% · ${freeGB}/${capGB}GB</span>
    </div>`;
  }).join('');
  return `<div class="hdd-row">${chips}</div>`;
}

// ── Renderização de device info ────────────────────────
function renderDevInfo(di) {
  if (!di) return '';
  const chips = [];
  if (di.device_name) chips.push(`<span class="dev-chip"><strong>${di.device_name}</strong></span>`);
  if (di.model)       chips.push(`<span class="dev-chip">Modelo: <strong>${di.model}</strong></span>`);
  if (di.firmware)    chips.push(`<span class="dev-chip">FW: <strong>${di.firmware}</strong></span>`);
  if (di.serial)      chips.push(`<span class="dev-chip">S/N: <strong>${di.serial}</strong></span>`);
  if (chips.length === 0) return '';
  return `<div class="dev-strip">${chips.join('')}</div>`;
}

// ── Renderização de um NVR ─────────────────────────────
function renderNvr(nvr) {
  const hc = hClass(nvr.health);
  const uid = 'nvr_' + nvr.nvr_id.replace(/\W/g,'_');
  const ts = nvr.polled_at
    ? new Date(nvr.polled_at).toLocaleTimeString('pt-BR')
    : '?';
  const ms  = nvr.poll_duration_ms ? `${nvr.poll_duration_ms}ms` : '';
  const host = nvr.port ? `${nvr.host}:${nvr.port}` : nvr.host;
  let body;
  if (!nvr.reachable) {
    body = `<div class="nvr-err-body">⚠ Inacessível — ${nvr.error || 'sem resposta'}</div>`;
  } else {
    body = `<div class="nvr-body">
      ${renderDevInfo(nvr.device_info)}
      ${renderHdds(nvr.hdds)}
      ${renderCams(nvr.cameras)}
    </div>`;
  }

  return `<div class="nvr-card h-${hc}" id="${uid}">
    <div class="nvr-head" onclick="toggleNvr('${uid}')">
      <span class="nvr-dot ${hc}"></span>
      <div class="nvr-names">
        <div class="nvr-title">${nvr.name}</div>
        <div class="nvr-meta">${host} · ${ts}</div>
      </div>
      <div class="nvr-counts">
        <div class="nvr-cnt"><span class="n ok">${nvr.cameras_online}</span><span class="l">Online</span></div>
        <div class="nvr-cnt"><span class="n err">${nvr.cameras_offline}</span><span class="l">Offline</span></div>
        <div class="nvr-cnt"><span class="n">${nvr.cameras_total}</span><span class="l">Total</span></div>
      </div>
      <div class="nvr-ms">${ms}</div>
      <span class="nvr-arrow">▶</span>
    </div>
    ${body}
  </div>`;
}

function toggleNvr(id) {
  document.getElementById(id)?.classList.toggle('open');
}

// ── Polling principal ──────────────────────────────────
function updateSummary(s) {
  document.getElementById('sNvrs').textContent  = s.nvrs_total;
  document.getElementById('sOk').textContent    = s.nvrs_ok;
  document.getElementById('sWarn').textContent  = s.nvrs_atencao;
  document.getElementById('sErr').textContent   = s.nvrs_inacessiveis;
  document.getElementById('sCTotal').textContent= s.cameras_total;
  document.getElementById('sCOn').textContent   = s.cameras_online;
  document.getElementById('sCOff').textContent  = s.cameras_offline;
}

async function carregarStatus() {
  setLoading(true);
  try {
    const res = await fetch(POLL_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    updateSummary(data.summary);

    const ts = new Date(data.timestamp).toLocaleString('pt-BR');
    document.getElementById('tsLine').innerHTML =
      `Última atualização: <span>${ts}</span>`;

    const stack = document.getElementById('nvrStack');
    if (!data.nvrs || data.nvrs.length === 0) {
      stack.innerHTML = `<div class="state-empty"><div class="ico">📭</div>Nenhum NVR ativo cadastrado.</div>`;
    } else {
      stack.innerHTML = data.nvrs.map(renderNvr).join('');
      // Abre automaticamente NVRs com problemas
      data.nvrs.forEach(n => {
        if (n.health !== 'OK') {
          document.getElementById('nvr_' + n.nvr_id.replace(/\W/g,'_'))?.classList.add('open');
        }
      });
    }

    // Atualiza eventos se o drawer estiver aberto
    if (document.getElementById('logDrawer').classList.contains('open')) {
      carregarLogs();
    }
  } catch(e) {
    document.getElementById('nvrStack').innerHTML =
      `<div class="state-empty"><div class="ico">⚠</div>Erro: ${e.message}</div>`;
    console.error(e);
  } finally {
    setLoading(false);
  }
}

// ── Drawer de eventos ──────────────────────────────────
function toggleLogs() {
  const d = document.getElementById('logDrawer');
  d.classList.toggle('open');
  if (d.classList.contains('open')) carregarLogs();
}

async function carregarLogs() {
  const todos = document.getElementById('chkTodos')?.checked ? '0' : '1';
  try {
    const res  = await fetch(`${EVENTOS_URL}?ativos=${todos}`);
    const data = await res.json();
    const list = document.getElementById('logList');
    const eventos = data.eventos || [];
    if (eventos.length === 0) {
      list.innerHTML = `<div style="padding:1.5rem;text-align:center;color:var(--text-3);font-size:12px;">
        ${todos === '1' ? 'Nenhum evento ativo no momento. ✅' : 'Nenhum evento registrado.'}
      </div>`;
      return;
    }
    list.innerHTML = eventos.map(e => {
      const resolvido = e.resolvido_em
        ? `<span style="color:var(--green);font-size:10px;">✓ resolvido ${e.resolvido_em}</span>`
        : `<span style="color:var(--red);font-size:10px;">● ativo</span>`;
      const detalhe = e.detalhe || e.mensagem || e.message || '';
      return `<div class="log-entry">
        <span class="log-ts">${e.aberto_em || e.ts || ''}</span>
        <span class="log-lvl ${e.resolvido_em ? 'INFO' : 'ERROR'}">${e.tipo || e.level || 'EVENTO'}</span>
        <div>
          <div class="log-msg">[${e.nvr_id || '–'}] ${e.descricao || e.message || detalhe}</div>
          <div class="log-detail">${resolvido}</div>
        </div>
      </div>`;
    }).join('');
  } catch(e) {
    document.getElementById('logList').innerHTML =
      `<div style="padding:1rem;color:var(--red);font-size:12px;font-family:monospace;">Erro: ${e.message}</div>`;
  }
}

// ── Auto-refresh 2 min ─────────────────────────────────
setInterval(carregarStatus, 120_000);

// ── Carga inicial ──────────────────────────────────────
carregarStatus();
</script>
{% endblock %}

{% extends "base.html" %}
{% block title %}Relatório de Monitoramento — Grupo Ronda{% endblock %}

{% block extra_css %}
<style>
  .rel-wrap { max-width: 680px; margin: 0 auto; padding: 2rem 1rem; }

  .rel-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 22px; font-weight: 800;
    color: var(--text); text-transform: uppercase; letter-spacing: .06em;
    display: flex; align-items: center; gap: 8px; margin-bottom: .3rem;
  }
  .rel-title::before {
    content: ''; width: 3px; height: 20px;
    background: var(--gold); border-radius: 2px;
  }
  .rel-sub { font-size: 12px; color: var(--text-3); margin-bottom: 2rem; }

  .rel-card {
    background: var(--bg-2); border: 1px solid var(--border);
    border-radius: 10px; padding: 1.5rem; margin-bottom: 1rem;
  }
  .rel-card-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 11px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: var(--text-3);
    margin-bottom: 1rem; padding-bottom: .6rem;
    border-bottom: 1px solid var(--border);
  }

  .date-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;
    margin-bottom: 1rem;
  }
  .form-group label {
    display: block; font-size: 11px; font-weight: 700;
    color: var(--text-3); text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 5px;
  }
  .form-group input[type=datetime-local] {
    width: 100%; background: var(--bg-3);
    border: 1px solid var(--border); border-radius: 7px;
    color: var(--text); padding: 9px 12px; font-size: 13px;
    font-family: 'DM Sans', sans-serif; outline: none;
    transition: border-color .15s;
    color-scheme: dark;
  }
  .form-group input:focus {
    border-color: rgba(245,196,0,.5);
  }

  /* Atalhos de período */
  .atalhos {
    display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: 1rem;
  }
  .atalho {
    font-size: 11px; font-weight: 600;
    background: var(--bg-3); border: 1px solid var(--border);
    border-radius: 5px; padding: 4px 10px; color: var(--text-2);
    cursor: pointer; transition: all .12s;
  }
  .atalho:hover { background: var(--accent-dim); border-color: var(--gold); color: var(--gold); }

  /* Formato */
  .fmt-group { display: flex; gap: .75rem; margin-bottom: 1.5rem; }
  .fmt-opt {
    flex: 1; background: var(--bg-3); border: 2px solid var(--border);
    border-radius: 8px; padding: .75rem; cursor: pointer;
    text-align: center; transition: all .15s;
  }
  .fmt-opt:hover { border-color: rgba(245,196,0,.4); }
  .fmt-opt.selected { border-color: var(--gold); background: var(--accent-dim); }
  .fmt-opt input { display: none; }
  .fmt-opt .ico { font-size: 22px; display: block; margin-bottom: 4px; }
  .fmt-opt .lbl { font-size: 12px; font-weight: 700; color: var(--text); }
  .fmt-opt .desc { font-size: 10px; color: var(--text-3); margin-top: 2px; }

  /* Botão gerar */
  .btn-gerar {
    width: 100%; background: var(--gold); color: #111;
    border: none; border-radius: 8px; padding: 12px;
    font-weight: 800; font-size: 14px; letter-spacing: .05em;
    text-transform: uppercase; cursor: pointer;
    display: flex; align-items: center; justify-content: center; gap: 8px;
    transition: all .15s;
  }
  .btn-gerar:hover { opacity: .9; box-shadow: 0 4px 16px rgba(245,196,0,.3); }
  .btn-gerar:disabled { opacity: .4; cursor: not-allowed; }
  .btn-gerar .spin {
    width: 16px; height: 16px;
    border: 2px solid #0005; border-top-color: #000;
    border-radius: 50%; animation: rg-spin .6s linear infinite; display: none;
  }
  .btn-gerar.loading .spin { display: block; }
  @keyframes rg-spin { to { transform: rotate(360deg); } }

  /* Mensagem de erro */
  .msg-erro {
    display: none; margin-top: .75rem; padding: .65rem 1rem;
    background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.3);
    border-radius: 7px; font-size: 12px; color: var(--red);
  }
  .msg-erro.vis { display: block; }

  /* Info período */
  .periodo-info {
    font-size: 11px; color: var(--text-3); margin-top: .5rem;
    text-align: center;
  }
</style>
{% endblock %}

{% block content %}
<div class="rel-wrap">

  <div class="rel-title">📊 Relatório de Monitoramento</div>
  <div class="rel-sub">Gera relatório técnico de NVRs e câmeras monitorados no período selecionado</div>

  <div class="rel-card">
    <div class="rel-card-title">Período</div>

    <!-- Atalhos rápidos -->
    <div class="atalhos">
      <span class="atalho" onclick="setPeriodo(1)">Últimas 24h</span>
      <span class="atalho" onclick="setPeriodo(7)">Últimos 7 dias</span>
      <span class="atalho" onclick="setPeriodo(15)">Últimos 15 dias</span>
      <span class="atalho" onclick="setPeriodo(30)">Últimos 30 dias</span>
      <span class="atalho" onclick="setHoje()">Hoje</span>
      <span class="atalho" onclick="setSemanaAtual()">Semana atual</span>
      <span class="atalho" onclick="setMesAtual()">Mês atual</span>
    </div>

    <div class="date-grid">
      <div class="form-group">
        <label>Data / Hora Início</label>
        <input type="datetime-local" id="dtInicio" onchange="atualizarInfo()">
      </div>
      <div class="form-group">
        <label>Data / Hora Fim</label>
        <input type="datetime-local" id="dtFim" onchange="atualizarInfo()">
      </div>
    </div>

    <div class="periodo-info" id="periodoInfo"></div>
  </div>

  <div class="rel-card">
    <div class="rel-card-title">Formato de Saída</div>
    <div class="fmt-group">
      <label class="fmt-opt selected" onclick="selecionarFmt(this, 'pdf')">
        <input type="radio" name="fmt" value="pdf" checked>
        <span class="ico">📄</span>
        <div class="lbl">PDF</div>
        <div class="desc">Relatório formatado, papel timbrado Grupo Ronda</div>
      </label>
      <label class="fmt-opt" onclick="selecionarFmt(this, 'xlsx')">
        <input type="radio" name="fmt" value="xlsx">
        <span class="ico">📊</span>
        <div class="lbl">Excel</div>
        <div class="desc">Planilha com 4 abas: Resumo, NVRs, Eventos, Câmeras</div>
      </label>
    </div>

    <button class="btn-gerar" id="btnGerar" onclick="gerarRelatorio()">
      <span class="spin" id="btnSpin"></span>
      <span id="btnTxt">⬇ Gerar e Baixar Relatório</span>
    </button>
    <div class="msg-erro" id="msgErro"></div>
  </div>

  <!-- Info sobre coleta -->
  <div style="font-size:11px;color:var(--text-3);text-align:center;line-height:1.6;">
    O relatório é gerado a partir dos dados coletados automaticamente a cada 5 minutos.<br>
    Períodos sem dados indicam que o sistema estava offline ou o NVR não havia sido cadastrado.
  </div>

</div>
{% endblock %}

{% block extra_js %}
<script>
let fmtSelecionado = 'pdf';

function selecionarFmt(el, fmt) {
  document.querySelectorAll('.fmt-opt').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  fmtSelecionado = fmt;
}

function _toLocalInput(d) {
  // Converte Date para string yyyy-MM-ddTHH:mm (fuso local)
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function setPeriodo(dias) {
  const fim = new Date();
  const ini = new Date(fim - dias * 86400000);
  document.getElementById('dtInicio').value = _toLocalInput(ini);
  document.getElementById('dtFim').value    = _toLocalInput(fim);
  atualizarInfo();
}

function setHoje() {
  const hoje = new Date();
  const ini  = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate(), 0, 0);
  document.getElementById('dtInicio').value = _toLocalInput(ini);
  document.getElementById('dtFim').value    = _toLocalInput(hoje);
  atualizarInfo();
}

function setSemanaAtual() {
  const hoje = new Date();
  const dow  = hoje.getDay() || 7;
  const ini  = new Date(hoje);
  ini.setDate(hoje.getDate() - dow + 1);
  ini.setHours(0, 0, 0, 0);
  document.getElementById('dtInicio').value = _toLocalInput(ini);
  document.getElementById('dtFim').value    = _toLocalInput(hoje);
  atualizarInfo();
}

function setMesAtual() {
  const hoje = new Date();
  const ini  = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
  document.getElementById('dtInicio').value = _toLocalInput(ini);
  document.getElementById('dtFim').value    = _toLocalInput(hoje);
  atualizarInfo();
}

function atualizarInfo() {
  const ini = document.getElementById('dtInicio').value;
  const fim = document.getElementById('dtFim').value;
  const el  = document.getElementById('periodoInfo');
  if (!ini || !fim) { el.textContent = ''; return; }
  const diff = (new Date(fim) - new Date(ini)) / 3600000;
  if (diff <= 0) {
    el.textContent = '⚠ A data fim deve ser maior que a data início';
    el.style.color = 'var(--red)';
  } else if (diff > 744) {
    el.textContent = '⚠ Período máximo: 31 dias';
    el.style.color = 'var(--red)';
  } else {
    const h = Math.floor(diff);
    const m = Math.round((diff - h) * 60);
    el.textContent = `Período selecionado: ${h}h ${m}min`;
    el.style.color = 'var(--text-3)';
  }
}

async function gerarRelatorio() {
  const ini = document.getElementById('dtInicio').value;
  const fim = document.getElementById('dtFim').value;
  const erro = document.getElementById('msgErro');
  erro.classList.remove('vis');

  if (!ini || !fim) {
    erro.textContent = 'Selecione o período antes de gerar.';
    erro.classList.add('vis'); return;
  }
  if (new Date(fim) <= new Date(ini)) {
    erro.textContent = 'A data fim deve ser maior que a data início.';
    erro.classList.add('vis'); return;
  }

  const btn = document.getElementById('btnGerar');
  const spin = document.getElementById('btnSpin');
  const txt  = document.getElementById('btnTxt');
  btn.disabled = true;
  btn.classList.add('loading');
  spin.style.display = 'block';
  txt.textContent = 'Gerando relatório…';

  try {
    const url = `{{ url_for('conferencia.relatorio_gerar') }}?dt_inicio=${ini}&dt_fim=${fim}&fmt=${fmtSelecionado}`;
    const resp = await fetch(url);

    if (!resp.ok) {
      const data = await resp.json();
      throw new Error(data.error || `HTTP ${resp.status}`);
    }

    // Força download do arquivo
    const blob = await resp.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    const ext  = fmtSelecionado;
    const ini_ = ini.replace('T','_').replace(':','h').slice(0,14);
    const fim_ = fim.replace('T','_').replace(':','h').slice(0,14);
    link.download = `relatorio_ronda_${ini_}_${fim_}.${ext}`;
    link.click();
    URL.revokeObjectURL(link.href);

  } catch(e) {
    erro.textContent = `Erro: ${e.message}`;
    erro.classList.add('vis');
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
    spin.style.display = 'none';
    txt.textContent = '⬇ Gerar e Baixar Relatório';
  }
}

// Define padrão: últimas 24h
setPeriodo(1);
</script>
{% endblock %}

{% extends "base.html" %}
{% block title %}Central de Alarmes — Grupo Ronda{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Central de Alarmes</h1>
    <button onclick="carregarAlertas()" class="btn btn-primary">↻ Atualizar</button>
</div>

<!-- CARDS RESUMO -->
<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin-bottom:1.5rem;">
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #6c757d;">
        <div style="font-size:32px; font-weight:700; color:#e0e0e0;" id="card-total">{{ total }}</div>
        <div style="font-size:12px; color:#6c757d; margin-top:4px;">📡 Total</div>
    </div>
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #f5c400;">
        <div style="font-size:32px; font-weight:700; color:#d4a000;" id="card-pendente">{{ pendentes }}</div>
        <div style="font-size:12px; color:#6c757d; margin-top:4px;">⚠️ Pendentes</div>
    </div>
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #dc3545;">
        <div style="font-size:32px; font-weight:700; color:#dc3545;" id="card-deteccao-falsa">{{ deteccoes_falsas|default(0) }}</div>
        <div style="font-size:12px; color:#6c757d; margin-top:4px;">Detecção Falsa</div>
    </div>
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #28a745;">
        <div style="font-size:32px; font-weight:700; color:#28a745;" id="card-tratado">{{ tratados }}</div>
        <div style="font-size:12px; color:#6c757d; margin-top:4px;">✅ Tratados</div>
    </div>
</div>

<!-- FILTROS -->
<div class="card" style="margin-bottom:1rem;">
    <div style="display:flex; flex-wrap:wrap; gap:1rem; align-items:flex-end;">
        <div>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:4px;">STATUS</label>
            <select id="f-status" class="form-select">
                <option value="todos">Todos</option>
                <option value="pendente" selected>Pendente</option>
                <option value="tratado">Tratado</option>
                <option value="deteccao_falsa">Detecção Falsa</option>
            </select>
        </div>
        <div>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:4px;">UFV</label>
            <select id="f-ufv" class="form-select">
                <option value="">Todas</option>
                {% for ufv in ufvs %}
                <option value="{{ ufv }}">{{ ufv }}</option>
                {% endfor %}
            </select>
        </div>
        <div>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:4px;">NVR</label>
            <select id="f-nvr" class="form-select">
                <option value="">Todos</option>
                {% for nvr in nvrs %}
                <option value="{{ nvr.nvr_id }}">{{ nvr.nvr_nome }}</option>
                {% endfor %}
            </select>
        </div>
        <div>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:4px;">DE</label>
            <input type="date" id="f-data-inicio" class="form-select">
        </div>
        <div>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:4px;">ATÉ</label>
            <input type="date" id="f-data-fim" class="form-select">
        </div>
        <div style="display:flex; gap:8px;">
            <button onclick="aplicarFiltros()" class="btn btn-success">🔍 Filtrar</button>
            <button onclick="limparFiltros()" class="btn btn-primary">✕ Limpar</button>
        </div>
    </div>
</div>

<!-- TABELA -->
<div class="card">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <div class="card-title" style="margin-bottom:0;">Registros de Alarme</div>
        <span style="font-size:13px; color:#888;" id="tabela-count">Carregando...</span>
    </div>

    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Data / Hora</th>
                <th>UFV</th>
                <th>NVR</th>
                <th>Local</th>
                <th>Pessoas</th>
                <th>Status</th>
                <th>Responsável</th>
                <th>Ações</th>
            </tr>
        </thead>
        <tbody id="tbody-alertas">
            <tr><td colspan="9" style="text-align:center; color:#6c757d; padding:2rem;">⏳ Carregando...</td></tr>
        </tbody>
    </table>

    <div id="paginacao" style="display:flex; justify-content:center; gap:6px; padding:1rem; border-top:1px solid #e9ecef;"></div>
</div>

<!-- MODAL TRATATIVA -->
<div id="modal-overlay" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6);
     z-index:999; align-items:center; justify-content:center;">
    <div style="background:#fff; border-radius:12px; width:100%; max-width:760px; max-height:92vh;
                overflow-y:auto; border-top:3px solid #f5c400; box-shadow:0 20px 50px rgba(0,0,0,0.4);">

        <div style="background:#111; padding:14px 20px; display:flex; justify-content:space-between; align-items:center;">
            <span style="color:#fff; font-weight:700; font-size:15px;" id="modal-titulo">Alerta</span>
            <button onclick="fecharModal()" style="background:none; border:none; color:#aaa; font-size:20px; cursor:pointer;">✕</button>
        </div>

        <div style="padding:20px;">
            <!-- Área da imagem de detecção YOLO -->
            <div id="modal-img-wrapper" style="display:none; background:#000; border-radius:8px;
                 margin-bottom:16px; overflow:hidden; position:relative; text-align:center; min-height:80px;">
                <img id="modal-img" style="max-width:100%; max-height:440px; object-fit:contain;
                     display:block; margin:0 auto;">
                <div id="modal-img-label" style="position:absolute; top:8px; left:8px;
                     background:rgba(220,53,69,0.85); color:#fff; font-size:11px; font-weight:700;
                     padding:3px 9px; border-radius:4px; letter-spacing:.5px;">
                    🎯 DETECÇÃO YOLO
                </div>
                <div id="modal-img-erro" style="display:none; color:#aaa; padding:32px; font-size:13px;">
                    📷 Imagem não disponível
                </div>
            </div>

            <div id="modal-info-grid" style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px; color:#ccc;"></div>

            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:6px;">DESCRIÇÃO DA TRATATIVA</label>
            <textarea id="modal-tratativa" style="width:100%; padding:10px; border:1px solid #2a2a2a; border-radius:6px;
                      font-size:13px; min-height:80px; resize:vertical; background:#181818; color:#e0e0e0;" placeholder="Descreva o que foi verificado..."></textarea>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin:12px 0 6px;">STATUS</label>
            <input type="hidden" id="modal-status" value="pendente">
            <div class="status-toggle" id="status-toggle">
                <button type="button" class="status-option status-tratado" data-status="tratado" onclick="setModalStatus('tratado')">Tratado</button>
                <button type="button" class="status-option status-pendente" data-status="pendente" onclick="setModalStatus('pendente')">Pendente</button>
                <button type="button" class="status-option status-falsa" data-status="deteccao_falsa" onclick="setModalStatus('deteccao_falsa')">Detecção Falsa</button>
            </div>

            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin:12px 0 6px;">MOTIVO RÁPIDO</label>
            <div id="motivos-wrap" class="motivos-wrap"></div>

            <div style="display:flex; gap:8px; margin-top:16px; justify-content:flex-end;">
                <button id="btn-reabrir" onclick="reabrirAlerta()" class="btn btn-primary btn-sm" style="display:none; margin-right:auto;">↩ Reabrir</button>
                <button onclick="fecharModal()" class="btn btn-primary btn-sm">Cancelar</button>
                <button onclick="salvarTratativa()" class="btn btn-success btn-sm">💾 Salvar</button>
            </div>
        </div>
    </div>
</div>

<!-- TOAST -->
<div id="toast-container" style="position:fixed; bottom:24px; right:24px; display:flex; flex-direction:column; gap:8px; z-index:9000;"></div>

<style>
.form-select {
    font-size:13px; padding:7px 10px; border:1px solid #2a2a2a;
    border-radius:6px; background:#181818; color:#e0e0e0; outline:none;
    min-width:130px;
}
.form-select:focus { border-color:#f5c400; box-shadow:0 0 0 3px rgba(245,196,0,0.12); }
.badge-pendente  { background:rgba(220,53,69,0.2); color:#f88; border:1px solid rgba(220,53,69,0.4); padding:3px 9px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-em_tratativa { background:rgba(245,196,0,0.15); color:#f5c400; border:1px solid rgba(245,196,0,0.35); padding:3px 9px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-tratado   { background:rgba(25,135,84,0.2); color:#6ee7a0; border:1px solid rgba(25,135,84,0.4); padding:3px 9px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-deteccao_falsa { background:rgba(108,117,125,0.22); color:#d7dde3; border:1px solid rgba(108,117,125,0.45); padding:3px 9px; border-radius:20px; font-size:11px; font-weight:600; }
.row-pendente td:first-child { border-left:3px solid rgba(220,53,69,0.8); }
.row-em_tratativa td:first-child { border-left:3px solid rgba(245,196,0,0.8); }
.row-tratado td:first-child { border-left:3px solid rgba(25,135,84,0.8); }
.row-deteccao_falsa td:first-child { border-left:3px solid rgba(108,117,125,0.8); }
.status-toggle { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:6px; }
.status-option { border:1px solid #2a2a2a; border-radius:6px; background:#181818; color:#e0e0e0; padding:10px 12px; font-size:13px; font-weight:700; cursor:pointer; }
.status-option:hover { border-color:#f5c400; }
.status-option.active.status-tratado { background:rgba(25,135,84,0.18); color:#6ee7a0; border-color:rgba(25,135,84,0.65); }
.status-option.active.status-pendente { background:rgba(245,196,0,0.16); color:#f5c400; border-color:rgba(245,196,0,0.65); }
.status-option.active.status-falsa { background:rgba(220,53,69,0.18); color:#ff8a95; border-color:rgba(220,53,69,0.65); }
.motivos-wrap { display:flex; flex-wrap:wrap; gap:8px; }
.motivo-chip { border:1px solid #2a2a2a; border-radius:20px; background:#181818; color:#d0d0d0; padding:7px 11px; font-size:12px; cursor:pointer; }
.motivo-chip:hover { border-color:#f5c400; color:#fff; }
.motivo-chip.active { background:#f5c400; color:#111; border-color:#f5c400; font-weight:700; }
</style>

<script>
let paginaAtual = 1;
let totalPaginas = 1;
let alertaIdAtivo = null;
const STATUS_LABELS = { pendente:'Pendente', em_tratativa:'Em tratativa', tratado:'Tratado', deteccao_falsa:'Detecção Falsa' };
const MOTIVOS_STATUS = {
    tratado: [
        'Vigia realizando ronda.',
        'Presença autorizada.',
        'Ocorrência verificada e tratada.',
        'Responsável acionado.',
        'Sem risco após verificação.'
    ],
    pendente: [
        'Imagem inconclusiva.',
        'Aguardando confirmação.',
        'Necessário contato com a equipe.',
        'Monitoramento em andamento.',
        'Aguardando nova verificação.'
    ],
    deteccao_falsa: [
        'Detecção falsa por sombra/reflexo.',
        'Detecção falsa por vegetação.',
        'Detecção falsa por animal.',
        'Detecção falsa por objeto fixo.',
        'Baixa qualidade da imagem.',
        'Erro de IA.'
    ]
};
let motivosSelecionados = [];

document.addEventListener('DOMContentLoaded', () => {
    carregarAlertas();
    setInterval(() => { atualizarCards(); if (paginaAtual===1) carregarAlertas(false); }, 30000);
});

function setModalStatus(status, sugerir=true) {
    const normalizado = ['tratado', 'pendente', 'deteccao_falsa'].includes(status) ? status : 'pendente';
    document.getElementById('modal-status').value = normalizado;
    document.querySelectorAll('.status-option').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.status === normalizado);
    });
    motivosSelecionados = [];
    renderMotivos(normalizado);
    if (sugerir && !document.getElementById('modal-tratativa').value.trim()) {
        const primeiro = MOTIVOS_STATUS[normalizado]?.[0] || '';
        document.getElementById('modal-tratativa').value = primeiro;
    }
}

function renderMotivos(status) {
    const wrap = document.getElementById('motivos-wrap');
    if (!wrap) return;
    const motivos = MOTIVOS_STATUS[status] || [];
    wrap.innerHTML = motivos.map(motivo => `
        <button type="button" class="motivo-chip" data-motivo="${motivo}" onclick="toggleMotivo(this)">${motivo.replace(/\.$/, '')}</button>
    `).join('');
}

function toggleMotivo(btn) {
    const motivo = btn.dataset.motivo;
    btn.classList.toggle('active');
    if (btn.classList.contains('active')) {
        if (!motivosSelecionados.includes(motivo)) motivosSelecionados.push(motivo);
    } else {
        motivosSelecionados = motivosSelecionados.filter(item => item !== motivo);
    }
    if (motivosSelecionados.length) {
        document.getElementById('modal-tratativa').value = motivosSelecionados.join(' ');
    }
}
function getFiltros() {
    return {
        status:      document.getElementById('f-status').value,
        ufv:         document.getElementById('f-ufv').value,
        nvr:         document.getElementById('f-nvr').value,
        data_inicio: document.getElementById('f-data-inicio').value,
        data_fim:    document.getElementById('f-data-fim').value,
    };
}

function aplicarFiltros() { paginaAtual = 1; carregarAlertas(); }

function limparFiltros() {
    document.getElementById('f-status').value = 'todos';
    document.getElementById('f-ufv').value = '';
    document.getElementById('f-nvr').value = '';
    document.getElementById('f-data-inicio').value = '';
    document.getElementById('f-data-fim').value = '';
    paginaAtual = 1;
    carregarAlertas();
}

async function carregarAlertas(loading=true) {
    const tbody = document.getElementById('tbody-alertas');
    if (loading) tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#888;padding:2rem;">⏳ Carregando...</td></tr>';

    const f = getFiltros();
    const p = new URLSearchParams({ page: paginaAtual, per_page: 20, status: f.status, ufv: f.ufv, nvr: f.nvr });
    if (f.data_inicio) p.set('data_inicio', f.data_inicio);
    if (f.data_fim)    p.set('data_fim',    f.data_fim);

    try {
        const resp = await fetch(`/api/alarmes?${p}`);
        const data = await resp.json();
        totalPaginas = data.pages || 1;
        renderTabela(data.alertas, data.total);
        renderPaginacao(data.total, data.page, data.pages);
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:#dc3545;padding:2rem;">❌ Erro: ${e.message}</td></tr>`;
    }
}

function renderTabela(alertas, total) {
    const tbody = document.getElementById('tbody-alertas');
    document.getElementById('tabela-count').textContent = `${total} registro(s)`;

    if (!alertas.length) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#888;padding:2rem;">Nenhum alerta encontrado.</td></tr>';
        return;
    }

    tbody.innerHTML = alertas.map(a => `
    <tr class="row-${a.status}">
        <td style="font-size:12px;color:#6c757d;">#${a.id}</td>
        <td style="font-size:12px;white-space:nowrap;">${(a.detectado_em||'—').slice(0,16).replace('T',' ')}</td>
        <td>${a.ufv}</td>
        <td style="font-weight:600;">${a.nvr_nome}</td>
        <td>${a.local_preset}</td>
        <td style="text-align:center;font-weight:700;color:${a.pessoas>0?'#dc3545':'#28a745'};">👤 ${a.pessoas}</td>
        <td><span class="badge-${a.status}">${STATUS_LABELS[a.status]||a.status}</span></td>
        <td style="font-size:12px;">${a.responsavel||'—'}</td>
        <td><button class="btn btn-primary btn-sm" onclick="abrirModal(${a.id})">Ver / Tratar</button></td>
    </tr>`).join('');
}

function renderPaginacao(total, page, pages) {
    const el = document.getElementById('paginacao');
    if (pages <= 1) { el.innerHTML=''; return; }
    let h = `<button class="btn btn-primary btn-sm" onclick="irPagina(${page-1})" ${page<=1?'disabled':''}>← Ant</button>`;
    for (let i=Math.max(1,page-2); i<=Math.min(pages,page+2); i++)
        h += `<button class="btn btn-sm" style="${i===page?'background:#f5c400;color:#111;':'background:#1e1e1e;color:#ccc;'}border:none;" onclick="irPagina(${i})">${i}</button>`;
    h += `<button class="btn btn-primary btn-sm" onclick="irPagina(${page+1})" ${page>=pages?'disabled':''}>Próx →</button>`;
    el.innerHTML = h;
}

function irPagina(p) { if(p<1||p>totalPaginas) return; paginaAtual=p; carregarAlertas(); window.scrollTo({top:0,behavior:'smooth'}); }

async function abrirModal(id) {
    alertaIdAtivo = id;
    try {
        const a = await fetch(`/api/alarmes/${id}`).then(r=>r.json());
        document.getElementById('modal-titulo').textContent = `Alerta #${a.id} — ${a.local_preset}`;

        // --- Exibição da imagem de detecção YOLO ---
        const wrapper = document.getElementById('modal-img-wrapper');
        const img     = document.getElementById('modal-img');
        const erroDiv = document.getElementById('modal-img-erro');

        if (a.imagem_path) {
            wrapper.style.display = 'block';
            img.style.display     = 'block';
            erroDiv.style.display = 'none';
            img.src = `/relatorios/${a.imagem_path}`;
            img.onerror = () => {
                // Tenta fallback: snapshot original sem sufixo _deteccao
                const fallback = img.src.replace('_deteccao.jpg', '.jpg');
                if (img.src !== fallback) {
                    img.src = fallback;
                    document.getElementById('modal-img-label').textContent = '📷 Snapshot';
                } else {
                    img.style.display     = 'none';
                    erroDiv.style.display = 'block';
                }
            };
        } else {
            wrapper.style.display = 'none';
        }
        // -------------------------------------------

        const dataFmt = (a.detectado_em||'—').slice(0,16).replace('T',' ');
        document.getElementById('modal-info-grid').innerHTML = `
            <div><label style="font-size:11px;font-weight:700;color:#888;">UFV</label><div style="font-size:13px;">${a.ufv||'—'}</div></div>
            <div><label style="font-size:11px;font-weight:700;color:#888;">NVR</label><div style="font-size:13px;">${a.nvr_nome}</div></div>
            <div><label style="font-size:11px;font-weight:700;color:#888;">LOCAL</label><div style="font-size:13px;">${a.local_preset}</div></div>
            <div><label style="font-size:11px;font-weight:700;color:#888;">PESSOAS</label><div style="font-size:13px;font-weight:700;color:#dc3545;">👤 ${a.pessoas}</div></div>
            <div><label style="font-size:11px;font-weight:700;color:#888;">DETECTADO EM</label><div style="font-size:13px;">${dataFmt}</div></div>
            <div><label style="font-size:11px;font-weight:700;color:#888;">STATUS</label><div><span class="badge-${a.status}">${STATUS_LABELS[a.status]||a.status}</span></div></div>
            ${a.tratativa?`<div style="grid-column:1/-1"><label style="font-size:11px;font-weight:700;color:#888;">TRATATIVA</label><div style="font-size:13px;">${a.tratativa}</div></div>`:''}`;

        document.getElementById('modal-tratativa').value = a.tratativa||'';
        setModalStatus(['tratado', 'pendente', 'deteccao_falsa'].includes(a.status) ? a.status : 'pendente', false);
        document.getElementById('btn-reabrir').style.display = a.status!=='pendente'?'inline-flex':'none';
        document.getElementById('modal-overlay').style.display = 'flex';
    } catch(e) { toast('Erro ao carregar: '+e.message, 'error'); }
}

function fecharModal() {
    document.getElementById('modal-overlay').style.display='none';
    document.getElementById('modal-img-wrapper').style.display='none';
    document.getElementById('modal-img-label').textContent='🎯 DETECÇÃO YOLO';
    alertaIdAtivo=null;
}

async function salvarTratativa() {
    if (!alertaIdAtivo) return;
    const tratativa = document.getElementById('modal-tratativa').value.trim();
    const status    = document.getElementById('modal-status').value;
    try {
        const data = await fetch(`/api/alarmes/${alertaIdAtivo}/tratar`,{
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({tratativa,status})
        }).then(r=>r.json());
        if (data.ok) { toast('Tratativa salva!','ok'); fecharModal(); carregarAlertas(false); atualizarCards(); }
        else toast('Erro: '+(data.erro||'falha'),'error');
    } catch(e) { toast('Erro: '+e.message,'error'); }
}

async function reabrirAlerta() {
    if (!alertaIdAtivo||!confirm('Reabrir como Pendente?')) return;
    const data = await fetch(`/api/alarmes/${alertaIdAtivo}/reabrir`,{method:'POST'}).then(r=>r.json());
    if (data.ok) { toast('Alerta reaberto!','ok'); fecharModal(); carregarAlertas(false); atualizarCards(); }
}

async function atualizarCards() {
    try {
        const d = await fetch('/api/alarmes/resumo').then(r=>r.json());
        document.getElementById('card-total').textContent    = d.total;
        document.getElementById('card-pendente').textContent = d.pendentes;
        document.getElementById('card-deteccao-falsa').textContent = d.deteccoes_falsas ?? 0;
        document.getElementById('card-tratado').textContent  = d.tratados;
    } catch(_) {}
}

function toast(msg, tipo) {
    const el = document.createElement('div');
    el.style.cssText = `font-size:13px;padding:12px 18px;border-radius:8px;background:#fff;
        box-shadow:0 8px 32px rgba(0,0,0,.6);border-left:4px solid ${tipo==='ok'?'#198754':'#dc3545'};
        color:#e0e0e0;max-width:320px;`;
    el.textContent = msg;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(()=>el.remove(), 3500);
}

document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target===document.getElementById('modal-overlay')) fecharModal();
});
document.addEventListener('keydown', e => { if(e.key==='Escape') fecharModal(); });
</script>

{% endblock %}


{% extends "base.html" %}
{% block title %}Central de Alarmes — Grupo Ronda{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Central de Alarmes</h1>
    <button onclick="carregarAlertas()" class="btn btn-primary">↻ Atualizar</button>
</div>

<!-- CARDS RESUMO -->
<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin-bottom:1.5rem;">
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #6c757d;">
        <div style="font-size:32px; font-weight:700; color:#e0e0e0;" id="card-total">{{ total }}</div>
        <div style="font-size:12px; color:#6c757d; margin-top:4px;">📡 Total</div>
    </div>
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #f5c400;">
        <div style="font-size:32px; font-weight:700; color:#d4a000;" id="card-pendente">{{ pendentes }}</div>
        <div style="font-size:12px; color:#6c757d; margin-top:4px;">⚠️ Pendentes</div>
    </div>
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #dc3545;">
        <div style="font-size:32px; font-weight:700; color:#dc3545;" id="card-deteccao-falsa">{{ deteccoes_falsas|default(0) }}</div>
        <div style="font-size:12px; color:#6c757d; margin-top:4px;">Detecção Falsa</div>
    </div>
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #28a745;">
        <div style="font-size:32px; font-weight:700; color:#28a745;" id="card-tratado">{{ tratados }}</div>
        <div style="font-size:12px; color:#6c757d; margin-top:4px;">✅ Tratados</div>
    </div>
</div>

<!-- FILTROS -->
<div class="card" style="margin-bottom:1rem;">
    <div style="display:flex; flex-wrap:wrap; gap:1rem; align-items:flex-end;">
        <div>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:4px;">STATUS</label>
            <select id="f-status" class="form-select">
                <option value="todos">Todos</option>
                <option value="pendente" selected>Pendente</option>
                <option value="tratado">Tratado</option>
                <option value="deteccao_falsa">Detecção Falsa</option>
            </select>
        </div>
        <div>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:4px;">UFV</label>
            <select id="f-ufv" class="form-select">
                <option value="">Todas</option>
                {% for ufv in ufvs %}
                <option value="{{ ufv }}">{{ ufv }}</option>
                {% endfor %}
            </select>
        </div>
        <div>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:4px;">NVR</label>
            <select id="f-nvr" class="form-select">
                <option value="">Todos</option>
                {% for nvr in nvrs %}
                <option value="{{ nvr.nvr_id }}">{{ nvr.nvr_nome }}</option>
                {% endfor %}
            </select>
        </div>
        <div>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:4px;">DE</label>
            <input type="date" id="f-data-inicio" class="form-select">
        </div>
        <div>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:4px;">ATÉ</label>
            <input type="date" id="f-data-fim" class="form-select">
        </div>
        <div style="display:flex; gap:8px;">
            <button onclick="aplicarFiltros()" class="btn btn-success">🔍 Filtrar</button>
            <button onclick="limparFiltros()" class="btn btn-primary">✕ Limpar</button>
        </div>
    </div>
</div>

<!-- TABELA -->
<div class="card">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <div class="card-title" style="margin-bottom:0;">Registros de Alarme</div>
        <span style="font-size:13px; color:#888;" id="tabela-count">Carregando...</span>
    </div>

    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Data / Hora</th>
                <th>UFV</th>
                <th>NVR</th>
                <th>Local</th>
                <th>Pessoas</th>
                <th>Status</th>
                <th>Responsável</th>
                <th>Ações</th>
            </tr>
        </thead>
        <tbody id="tbody-alertas">
            <tr><td colspan="9" style="text-align:center; color:#6c757d; padding:2rem;">⏳ Carregando...</td></tr>
        </tbody>
    </table>

    <div id="paginacao" style="display:flex; justify-content:center; gap:6px; padding:1rem; border-top:1px solid #e9ecef;"></div>
</div>

<!-- MODAL TRATATIVA -->
<div id="modal-overlay" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6);
     z-index:999; align-items:center; justify-content:center;">
    <div style="background:#fff; border-radius:12px; width:100%; max-width:760px; max-height:92vh;
                overflow-y:auto; border-top:3px solid #f5c400; box-shadow:0 20px 50px rgba(0,0,0,0.4);">

        <div style="background:#111; padding:14px 20px; display:flex; justify-content:space-between; align-items:center;">
            <span style="color:#fff; font-weight:700; font-size:15px;" id="modal-titulo">Alerta</span>
            <button onclick="fecharModal()" style="background:none; border:none; color:#aaa; font-size:20px; cursor:pointer;">✕</button>
        </div>

        <div style="padding:20px;">
            <!-- Área da imagem de detecção YOLO -->
            <div id="modal-img-wrapper" style="display:none; background:#000; border-radius:8px;
                 margin-bottom:16px; overflow:hidden; position:relative; text-align:center; min-height:80px;">
                <img id="modal-img" style="max-width:100%; max-height:440px; object-fit:contain;
                     display:block; margin:0 auto;">
                <div id="modal-img-label" style="position:absolute; top:8px; left:8px;
                     background:rgba(220,53,69,0.85); color:#fff; font-size:11px; font-weight:700;
                     padding:3px 9px; border-radius:4px; letter-spacing:.5px;">
                    🎯 DETECÇÃO YOLO
                </div>
                <div id="modal-img-erro" style="display:none; color:#aaa; padding:32px; font-size:13px;">
                    📷 Imagem não disponível
                </div>
            </div>

            <div id="modal-info-grid" style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px; color:#ccc;"></div>

            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin-bottom:6px;">DESCRIÇÃO DA TRATATIVA</label>
            <textarea id="modal-tratativa" style="width:100%; padding:10px; border:1px solid #2a2a2a; border-radius:6px;
                      font-size:13px; min-height:80px; resize:vertical; background:#181818; color:#e0e0e0;" placeholder="Descreva o que foi verificado..."></textarea>
            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin:12px 0 6px;">STATUS</label>
            <input type="hidden" id="modal-status" value="pendente">
            <div class="status-toggle" id="status-toggle">
                <button type="button" class="status-option status-tratado" data-status="tratado" onclick="setModalStatus('tratado')">Tratado</button>
                <button type="button" class="status-option status-pendente" data-status="pendente" onclick="setModalStatus('pendente')">Pendente</button>
                <button type="button" class="status-option status-falsa" data-status="deteccao_falsa" onclick="setModalStatus('deteccao_falsa')">Detecção Falsa</button>
            </div>

            <label style="font-size:12px; font-weight:700; color:#888; display:block; margin:12px 0 6px;">MOTIVO RÁPIDO</label>
            <div id="motivos-wrap" class="motivos-wrap"></div>

            <div style="display:flex; gap:8px; margin-top:16px; justify-content:flex-end;">
                <button id="btn-reabrir" onclick="reabrirAlerta()" class="btn btn-primary btn-sm" style="display:none; margin-right:auto;">↩ Reabrir</button>
                <button onclick="fecharModal()" class="btn btn-primary btn-sm">Cancelar</button>
                <button onclick="salvarTratativa()" class="btn btn-success btn-sm">💾 Salvar</button>
            </div>
        </div>
    </div>
</div>

<!-- TOAST -->
<div id="toast-container" style="position:fixed; bottom:24px; right:24px; display:flex; flex-direction:column; gap:8px; z-index:9000;"></div>

<style>
.form-select {
    font-size:13px; padding:7px 10px; border:1px solid #2a2a2a;
    border-radius:6px; background:#181818; color:#e0e0e0; outline:none;
    min-width:130px;
}
.form-select:focus { border-color:#f5c400; box-shadow:0 0 0 3px rgba(245,196,0,0.12); }
.badge-pendente  { background:rgba(220,53,69,0.2); color:#f88; border:1px solid rgba(220,53,69,0.4); padding:3px 9px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-em_tratativa { background:rgba(245,196,0,0.15); color:#f5c400; border:1px solid rgba(245,196,0,0.35); padding:3px 9px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-tratado   { background:rgba(25,135,84,0.2); color:#6ee7a0; border:1px solid rgba(25,135,84,0.4); padding:3px 9px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-deteccao_falsa { background:rgba(108,117,125,0.22); color:#d7dde3; border:1px solid rgba(108,117,125,0.45); padding:3px 9px; border-radius:20px; font-size:11px; font-weight:600; }
.row-pendente td:first-child { border-left:3px solid rgba(220,53,69,0.8); }
.row-em_tratativa td:first-child { border-left:3px solid rgba(245,196,0,0.8); }
.row-tratado td:first-child { border-left:3px solid rgba(25,135,84,0.8); }
.row-deteccao_falsa td:first-child { border-left:3px solid rgba(108,117,125,0.8); }
.status-toggle { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:6px; }
.status-option { border:1px solid #2a2a2a; border-radius:6px; background:#181818; color:#e0e0e0; padding:10px 12px; font-size:13px; font-weight:700; cursor:pointer; }
.status-option:hover { border-color:#f5c400; }
.status-option.active.status-tratado { background:rgba(25,135,84,0.18); color:#6ee7a0; border-color:rgba(25,135,84,0.65); }
.status-option.active.status-pendente { background:rgba(245,196,0,0.16); color:#f5c400; border-color:rgba(245,196,0,0.65); }
.status-option.active.status-falsa { background:rgba(220,53,69,0.18); color:#ff8a95; border-color:rgba(220,53,69,0.65); }
.motivos-wrap { display:flex; flex-wrap:wrap; gap:8px; }
.motivo-chip { border:1px solid #2a2a2a; border-radius:20px; background:#181818; color:#d0d0d0; padding:7px 11px; font-size:12px; cursor:pointer; }
.motivo-chip:hover { border-color:#f5c400; color:#fff; }
.motivo-chip.active { background:#f5c400; color:#111; border-color:#f5c400; font-weight:700; }
</style>

<script>
let paginaAtual = 1;
let totalPaginas = 1;
let alertaIdAtivo = null;
const STATUS_LABELS = { pendente:'Pendente', em_tratativa:'Em tratativa', tratado:'Tratado', deteccao_falsa:'Detecção Falsa' };
const MOTIVOS_STATUS = {
    tratado: [
        'Vigia realizando ronda.',
        'Presença autorizada.',
        'Ocorrência verificada e tratada.',
        'Responsável acionado.',
        'Sem risco após verificação.'
    ],
    pendente: [
        'Imagem inconclusiva.',
        'Aguardando confirmação.',
        'Necessário contato com a equipe.',
        'Monitoramento em andamento.',
        'Aguardando nova verificação.'
    ],
    deteccao_falsa: [
        'Detecção falsa por sombra/reflexo.',
        'Detecção falsa por vegetação.',
        'Detecção falsa por animal.',
        'Detecção falsa por objeto fixo.',
        'Baixa qualidade da imagem.',
        'Erro de IA.'
    ]
};
let motivosSelecionados = [];

document.addEventListener('DOMContentLoaded', () => {
    carregarAlertas();
    setInterval(() => { atualizarCards(); if (paginaAtual===1) carregarAlertas(false); }, 30000);
});

function setModalStatus(status, sugerir=true) {
    const normalizado = ['tratado', 'pendente', 'deteccao_falsa'].includes(status) ? status : 'pendente';
    document.getElementById('modal-status').value = normalizado;
    document.querySelectorAll('.status-option').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.status === normalizado);
    });
    motivosSelecionados = [];
    renderMotivos(normalizado);
    if (sugerir && !document.getElementById('modal-tratativa').value.trim()) {
        const primeiro = MOTIVOS_STATUS[normalizado]?.[0] || '';
        document.getElementById('modal-tratativa').value = primeiro;
    }
}

function renderMotivos(status) {
    const wrap = document.getElementById('motivos-wrap');
    if (!wrap) return;
    const motivos = MOTIVOS_STATUS[status] || [];
    wrap.innerHTML = motivos.map(motivo => `
        <button type="button" class="motivo-chip" data-motivo="${motivo}" onclick="toggleMotivo(this)">${motivo.replace(/\.$/, '')}</button>
    `).join('');
}

function toggleMotivo(btn) {
    const motivo = btn.dataset.motivo;
    btn.classList.toggle('active');
    if (btn.classList.contains('active')) {
        if (!motivosSelecionados.includes(motivo)) motivosSelecionados.push(motivo);
    } else {
        motivosSelecionados = motivosSelecionados.filter(item => item !== motivo);
    }
    if (motivosSelecionados.length) {
        document.getElementById('modal-tratativa').value = motivosSelecionados.join(' ');
    }
}
function getFiltros() {
    return {
        status:      document.getElementById('f-status').value,
        ufv:         document.getElementById('f-ufv').value,
        nvr:         document.getElementById('f-nvr').value,
        data_inicio: document.getElementById('f-data-inicio').value,
        data_fim:    document.getElementById('f-data-fim').value,
    };
}

function aplicarFiltros() { paginaAtual = 1; carregarAlertas(); }

function limparFiltros() {
    document.getElementById('f-status').value = 'todos';
    document.getElementById('f-ufv').value = '';
    document.getElementById('f-nvr').value = '';
    document.getElementById('f-data-inicio').value = '';
    document.getElementById('f-data-fim').value = '';
    paginaAtual = 1;
    carregarAlertas();
}

async function carregarAlertas(loading=true) {
    const tbody = document.getElementById('tbody-alertas');
    if (loading) tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#888;padding:2rem;">⏳ Carregando...</td></tr>';

    const f = getFiltros();
    const p = new URLSearchParams({ page: paginaAtual, per_page: 20, status: f.status, ufv: f.ufv, nvr: f.nvr });
    if (f.data_inicio) p.set('data_inicio', f.data_inicio);
    if (f.data_fim)    p.set('data_fim',    f.data_fim);

    try {
        const resp = await fetch(`/api/alarmes?${p}`);
        const data = await resp.json();
        totalPaginas = data.pages || 1;
        renderTabela(data.alertas, data.total);
        renderPaginacao(data.total, data.page, data.pages);
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:#dc3545;padding:2rem;">❌ Erro: ${e.message}</td></tr>`;
    }
}

function renderTabela(alertas, total) {
    const tbody = document.getElementById('tbody-alertas');
    document.getElementById('tabela-count').textContent = `${total} registro(s)`;

    if (!alertas.length) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#888;padding:2rem;">Nenhum alerta encontrado.</td></tr>';
        return;
    }

    tbody.innerHTML = alertas.map(a => `
    <tr class="row-${a.status}">
        <td style="font-size:12px;color:#6c757d;">#${a.id}</td>
        <td style="font-size:12px;white-space:nowrap;">${(a.detectado_em||'—').slice(0,16).replace('T',' ')}</td>
        <td>${a.ufv}</td>
        <td style="font-weight:600;">${a.nvr_nome}</td>
        <td>${a.local_preset}</td>
        <td style="text-align:center;font-weight:700;color:${a.pessoas>0?'#dc3545':'#28a745'};">👤 ${a.pessoas}</td>
        <td><span class="badge-${a.status}">${STATUS_LABELS[a.status]||a.status}</span></td>
        <td style="font-size:12px;">${a.responsavel||'—'}</td>
        <td><button class="btn btn-primary btn-sm" onclick="abrirModal(${a.id})">Ver / Tratar</button></td>
    </tr>`).join('');
}

function renderPaginacao(total, page, pages) {
    const el = document.getElementById('paginacao');
    if (pages <= 1) { el.innerHTML=''; return; }
    let h = `<button class="btn btn-primary btn-sm" onclick="irPagina(${page-1})" ${page<=1?'disabled':''}>← Ant</button>`;
    for (let i=Math.max(1,page-2); i<=Math.min(pages,page+2); i++)
        h += `<button class="btn btn-sm" style="${i===page?'background:#f5c400;color:#111;':'background:#1e1e1e;color:#ccc;'}border:none;" onclick="irPagina(${i})">${i}</button>`;
    h += `<button class="btn btn-primary btn-sm" onclick="irPagina(${page+1})" ${page>=pages?'disabled':''}>Próx →</button>`;
    el.innerHTML = h;
}

function irPagina(p) { if(p<1||p>totalPaginas) return; paginaAtual=p; carregarAlertas(); window.scrollTo({top:0,behavior:'smooth'}); }

async function abrirModal(id) {
    alertaIdAtivo = id;
    try {
        const a = await fetch(`/api/alarmes/${id}`).then(r=>r.json());
        document.getElementById('modal-titulo').textContent = `Alerta #${a.id} — ${a.local_preset}`;

        // --- Exibição da imagem de detecção YOLO ---
        const wrapper = document.getElementById('modal-img-wrapper');
        const img     = document.getElementById('modal-img');
        const erroDiv = document.getElementById('modal-img-erro');

        if (a.imagem_path) {
            wrapper.style.display = 'block';
            img.style.display     = 'block';
            erroDiv.style.display = 'none';
            img.src = `/relatorios/${a.imagem_path}`;
            img.onerror = () => {
                // Tenta fallback: snapshot original sem sufixo _deteccao
                const fallback = img.src.replace('_deteccao.jpg', '.jpg');
                if (img.src !== fallback) {
                    img.src = fallback;
                    document.getElementById('modal-img-label').textContent = '📷 Snapshot';
                } else {
                    img.style.display     = 'none';
                    erroDiv.style.display = 'block';
                }
            };
        } else {
            wrapper.style.display = 'none';
        }
        // -------------------------------------------

        const dataFmt = (a.detectado_em||'—').slice(0,16).replace('T',' ');
        document.getElementById('modal-info-grid').innerHTML = `
            <div><label style="font-size:11px;font-weight:700;color:#888;">UFV</label><div style="font-size:13px;">${a.ufv||'—'}</div></div>
            <div><label style="font-size:11px;font-weight:700;color:#888;">NVR</label><div style="font-size:13px;">${a.nvr_nome}</div></div>
            <div><label style="font-size:11px;font-weight:700;color:#888;">LOCAL</label><div style="font-size:13px;">${a.local_preset}</div></div>
            <div><label style="font-size:11px;font-weight:700;color:#888;">PESSOAS</label><div style="font-size:13px;font-weight:700;color:#dc3545;">👤 ${a.pessoas}</div></div>
            <div><label style="font-size:11px;font-weight:700;color:#888;">DETECTADO EM</label><div style="font-size:13px;">${dataFmt}</div></div>
            <div><label style="font-size:11px;font-weight:700;color:#888;">STATUS</label><div><span class="badge-${a.status}">${STATUS_LABELS[a.status]||a.status}</span></div></div>
            ${a.tratativa?`<div style="grid-column:1/-1"><label style="font-size:11px;font-weight:700;color:#888;">TRATATIVA</label><div style="font-size:13px;">${a.tratativa}</div></div>`:''}`;

        document.getElementById('modal-tratativa').value = a.tratativa||'';
        setModalStatus(['tratado', 'pendente', 'deteccao_falsa'].includes(a.status) ? a.status : 'pendente', false);
        document.getElementById('btn-reabrir').style.display = a.status!=='pendente'?'inline-flex':'none';
        document.getElementById('modal-overlay').style.display = 'flex';
    } catch(e) { toast('Erro ao carregar: '+e.message, 'error'); }
}

function fecharModal() {
    document.getElementById('modal-overlay').style.display='none';
    document.getElementById('modal-img-wrapper').style.display='none';
    document.getElementById('modal-img-label').textContent='🎯 DETECÇÃO YOLO';
    alertaIdAtivo=null;
}

async function salvarTratativa() {
    if (!alertaIdAtivo) return;
    const tratativa = document.getElementById('modal-tratativa').value.trim();
    const status    = document.getElementById('modal-status').value;
    try {
        const data = await fetch(`/api/alarmes/${alertaIdAtivo}/tratar`,{
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({tratativa,status})
        }).then(r=>r.json());
        if (data.ok) { toast('Tratativa salva!','ok'); fecharModal(); carregarAlertas(false); atualizarCards(); }
        else toast('Erro: '+(data.erro||'falha'),'error');
    } catch(e) { toast('Erro: '+e.message,'error'); }
}

async function reabrirAlerta() {
    if (!alertaIdAtivo||!confirm('Reabrir como Pendente?')) return;
    const data = await fetch(`/api/alarmes/${alertaIdAtivo}/reabrir`,{method:'POST'}).then(r=>r.json());
    if (data.ok) { toast('Alerta reaberto!','ok'); fecharModal(); carregarAlertas(false); atualizarCards(); }
}

async function atualizarCards() {
    try {
        const d = await fetch('/api/alarmes/resumo').then(r=>r.json());
        document.getElementById('card-total').textContent    = d.total;
        document.getElementById('card-pendente').textContent = d.pendentes;
        document.getElementById('card-deteccao-falsa').textContent = d.deteccoes_falsas ?? 0;
        document.getElementById('card-tratado').textContent  = d.tratados;
    } catch(_) {}
}

function toast(msg, tipo) {
    const el = document.createElement('div');
    el.style.cssText = `font-size:13px;padding:12px 18px;border-radius:8px;background:#fff;
        box-shadow:0 8px 32px rgba(0,0,0,.6);border-left:4px solid ${tipo==='ok'?'#198754':'#dc3545'};
        color:#e0e0e0;max-width:320px;`;
    el.textContent = msg;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(()=>el.remove(), 3500);
}

document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target===document.getElementById('modal-overlay')) fecharModal();
});
document.addEventListener('keydown', e => { if(e.key==='Escape') fecharModal(); });
</script>

{% endblock %}


<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}Grupo Ronda{% endblock %}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --gold:        #f5c400;
            --gold-dim:    #c49a00;
            --gold-glow:   rgba(245,196,0,0.15);
            --gold-soft:   rgba(245,196,0,0.08);
            --bg:          #0a0a0b;
            --bg-2:        #111114;
            --bg-3:        #18181c;
            --bg-4:        #222228;
            --border:      rgba(255,255,255,0.07);
            --border-gold: rgba(245,196,0,0.3);
            --text:        #f0f0f0;
            --text-2:      #a0a0a8;
            --text-3:      #606068;
            --red:         #e84057;
            --red-soft:    rgba(232,64,87,0.12);
            --green:       #22c55e;
            --green-soft:  rgba(34,197,94,0.12);
            --orange:      #f97316;
            --orange-soft: rgba(249,115,22,0.12);
            --blue:        #3b82f6;
            --blue-soft:   rgba(59,130,246,0.12);
            --radius:      10px;
            --radius-lg:   16px;
            --shadow:      0 4px 24px rgba(0,0,0,0.4);
            --shadow-gold: 0 0 0 1px var(--border-gold), 0 4px 24px rgba(245,196,0,0.08);
        }

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'DM Sans', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            /* Subtle grid texture */
            background-image:
                linear-gradient(rgba(245,196,0,0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(245,196,0,0.02) 1px, transparent 1px);
            background-size: 48px 48px;
        }

        /* ── SCROLLBAR ───────────────────────────── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-2); }
        ::-webkit-scrollbar-thumb { background: var(--bg-4); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--gold-dim); }

        /* ── NAVBAR ──────────────────────────────── */
        nav {
            background: rgba(10,10,11,0.95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 0 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 56px;
            position: sticky;
            top: 0;
            z-index: 200;
        }
        nav::after {
            content: '';
            position: absolute;
            bottom: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--gold), transparent);
            opacity: 0.5;
        }

        .nav-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
            flex-shrink: 0;
        }
        .nav-brand img {
            height: 32px; width: 32px;
            object-fit: contain;
            border-radius: 6px;
            border: 1px solid var(--border-gold);
        }
        .nav-brand-text {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 18px;
            font-weight: 800;
            letter-spacing: 0.08em;
            color: var(--text);
            text-transform: uppercase;
        }
        .nav-brand-text span { color: var(--gold); }

        .nav-center {
            display: flex;
            align-items: center;
            gap: 2px;
        }
        .nav-sep {
            width: 1px;
            height: 18px;
            background: var(--border);
            margin: 0 6px;
        }
        .nav-center a {
            color: var(--text-2);
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            padding: 5px 11px;
            border-radius: 7px;
            transition: all 0.15s;
            white-space: nowrap;
            letter-spacing: 0.01em;
        }
        .nav-center a:hover {
            background: var(--gold-soft);
            color: var(--gold);
        }
        .nav-center a.active {
            background: var(--gold-soft);
            color: var(--gold);
            border: 1px solid var(--border-gold);
        }

        .nav-user {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
        }
        .nav-user-info {
            font-size: 12px;
            color: var(--text-3);
            text-align: right;
            line-height: 1.4;
        }
        .nav-user-info strong { color: var(--text-2); font-size: 13px; display: block; }
        .btn-logout {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-3);
            font-size: 12px;
            font-family: 'DM Sans', sans-serif;
            font-weight: 500;
            padding: 5px 12px;
            border-radius: 7px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.15s;
        }
        .btn-logout:hover {
            border-color: var(--red);
            color: var(--red);
            background: var(--red-soft);
        }

        /* ── CONTAINER ───────────────────────────── */
        .container {
            max-width: 1160px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }

        /* ── PAGE HEADER ─────────────────────────── */
        .page-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.75rem;
            padding-bottom: 1.25rem;
            border-bottom: 1px solid var(--border);
        }
        .page-header h1 {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 26px;
            font-weight: 800;
            color: var(--text);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* ── FLASH ALERTS ────────────────────────── */
        .alert {
            padding: 11px 16px;
            border-radius: var(--radius);
            margin-bottom: 1rem;
            font-size: 13px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            border: 1px solid transparent;
        }
        .alert-success { background: var(--green-soft);  border-color: rgba(34,197,94,0.25);   color: #4ade80; }
        .alert-danger  { background: var(--red-soft);    border-color: rgba(232,64,87,0.25);    color: #f87171; }
        .alert-warning { background: var(--orange-soft); border-color: rgba(249,115,22,0.25);   color: #fb923c; }
        .alert-info    { background: var(--blue-soft);   border-color: rgba(59,130,246,0.25);   color: #60a5fa; }

        /* ── CARDS ───────────────────────────────── */
        .card {
            background: var(--bg-2);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            transition: border-color 0.2s;
        }
        .card:hover { border-color: rgba(255,255,255,0.1); }
        .card-title {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 15px;
            font-weight: 700;
            color: var(--text);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 1.25rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card-title::before {
            content: '';
            width: 3px; height: 16px;
            background: var(--gold);
            border-radius: 2px;
            flex-shrink: 0;
        }

        /* ── STAT CARDS ──────────────────────────── */
        .stat-card {
            background: var(--bg-2);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.25rem 1.5rem;
            position: relative;
            overflow: hidden;
            transition: all 0.2s;
        }
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
        }
        .stat-card.gold::before   { background: var(--gold); }
        .stat-card.green::before  { background: var(--green); }
        .stat-card.red::before    { background: var(--red); }
        .stat-card.orange::before { background: var(--orange); }
        .stat-card.blue::before   { background: var(--blue); }
        .stat-card:hover { border-color: rgba(255,255,255,0.12); transform: translateY(-1px); }
        .stat-value {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 36px;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 4px;
        }
        .stat-label {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-3);
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        /* ── BUTTONS ─────────────────────────────── */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 8px 18px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            font-family: 'DM Sans', sans-serif;
            cursor: pointer;
            border: 1px solid transparent;
            text-decoration: none;
            transition: all 0.15s;
            white-space: nowrap;
        }
        .btn:active { transform: scale(0.97); }
        .btn-primary {
            background: var(--gold);
            color: #111;
            border-color: var(--gold);
        }
        .btn-primary:hover { background: #ffd633; box-shadow: 0 4px 16px rgba(245,196,0,0.3); }
        .btn-ghost {
            background: transparent;
            color: var(--text-2);
            border-color: var(--border);
        }
        .btn-ghost:hover { background: var(--bg-3); border-color: rgba(255,255,255,0.15); color: var(--text); }
        .btn-success {
            background: transparent;
            color: var(--green);
            border-color: rgba(34,197,94,0.4);
        }
        .btn-success:hover { background: var(--green-soft); }
        .btn-danger {
            background: transparent;
            color: var(--red);
            border-color: rgba(232,64,87,0.4);
        }
        .btn-danger:hover { background: var(--red-soft); }
        .btn-dark {
            background: var(--bg-3);
            color: var(--text-2);
            border-color: var(--border);
        }
        .btn-dark:hover { background: var(--bg-4); color: var(--text); }
        .btn-sm { padding: 5px 12px; font-size: 12px; }
        .btn-lg { padding: 11px 24px; font-size: 14px; }

        /* ── TABLES ──────────────────────────────── */
        .table-wrap {
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            overflow: hidden;
        }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        thead tr { background: var(--bg-3); }
        th {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-3);
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        td {
            padding: 11px 14px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
            color: var(--text-2);
        }
        tbody tr:last-child td { border-bottom: none; }
        tbody tr { transition: background 0.1s; }
        tbody tr:hover td { background: var(--bg-3); color: var(--text); }

        /* ── BADGES ──────────────────────────────── */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 9px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .badge-pendente    { background: var(--orange-soft); color: var(--orange); border: 1px solid rgba(249,115,22,0.3); }
        .badge-em_tratativa{ background: var(--blue-soft);   color: var(--blue);   border: 1px solid rgba(59,130,246,0.3); }
        .badge-tratado     { background: var(--green-soft);  color: var(--green);  border: 1px solid rgba(34,197,94,0.3); }
        .badge-success     { background: var(--green-soft);  color: var(--green);  border: 1px solid rgba(34,197,94,0.3); }
        .badge-danger      { background: var(--red-soft);    color: var(--red);    border: 1px solid rgba(232,64,87,0.3); }
        .badge-warning     { background: var(--orange-soft); color: var(--orange); border: 1px solid rgba(249,115,22,0.3); }
        .badge-info        { background: var(--blue-soft);   color: var(--blue);   border: 1px solid rgba(59,130,246,0.3); }
        .badge-secondary   { background: var(--bg-3);        color: var(--text-3); border: 1px solid var(--border); }

        /* ── FORMS ───────────────────────────────── */
        .form-group { margin-bottom: 1.1rem; }
        label {
            display: block;
            font-size: 11px;
            font-weight: 700;
            color: var(--text-3);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
        }
        input[type=text], input[type=password], input[type=email],
        input[type=number], input[type=date], select, textarea {
            width: 100%;
            padding: 9px 13px;
            background: var(--bg-3);
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 13px;
            font-family: 'DM Sans', sans-serif;
            color: var(--text);
            transition: all 0.15s;
            appearance: none;
        }
        input::placeholder, textarea::placeholder { color: var(--text-3); }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: var(--gold-dim);
            box-shadow: 0 0 0 3px var(--gold-soft);
            background: var(--bg-2);
        }
        select {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23606068' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 12px center;
            padding-right: 36px;
        }
        select option { background: var(--bg-3); color: var(--text); }
        textarea { resize: vertical; min-height: 80px; }
        small { font-size: 11px; color: var(--text-3); display: block; margin-top: 4px; }

        /* ── SECTION DIVIDER ─────────────────────── */
        .section-label {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--text-3);
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 1rem;
        }
        .section-label::after {
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border);
        }

        /* ── LOOP STATUS DOT ─────────────────────── */
        #nav-loop-dot {
            display: none;
            width: 7px; height: 7px;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 6px var(--green);
            animation: pulse-dot 2s infinite;
        }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50%       { opacity: 0.4; }
        }

        /* ── UTILITY ─────────────────────────────── */
        .text-gold   { color: var(--gold); }
        .text-red    { color: var(--red); }
        .text-green  { color: var(--green); }
        .text-muted  { color: var(--text-3); }
        .text-center { text-align: center; }
        .fw-bold     { font-weight: 700; }
        .gap-1       { gap: 8px; }
        .d-flex      { display: flex; }
        .align-center{ align-items: center; }

        /* ── MODAL BACKDROP ──────────────────────── */
        .modal-overlay {
            display: none;
            position: fixed; inset: 0;
            background: rgba(0,0,0,0.75);
            backdrop-filter: blur(4px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }
        .modal {
            background: var(--bg-2);
            border: 1px solid var(--border);
            border-top: 2px solid var(--gold);
            border-radius: var(--radius-lg);
            width: 100%;
            max-width: 600px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 24px 64px rgba(0,0,0,0.6);
        }
        .modal-header {
            background: var(--bg-3);
            padding: 14px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }
        .modal-title {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 15px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text);
        }
        .modal-close {
            background: none; border: none;
            color: var(--text-3); font-size: 20px;
            cursor: pointer; line-height: 1;
            transition: color 0.15s;
        }
        .modal-close:hover { color: var(--red); }
        .modal-body { padding: 20px; }
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>

{% if session.monitor_id %}
<nav>
    <a class="nav-brand" href="{{ url_for('dashboard.dashboard') }}">
        <img src="{{ url_for('static', filename='img/logo.jpeg') }}" alt="Grupo Ronda">
        <span class="nav-brand-text">GRUPO <span>RONDA</span></span>
    </a>

    <div class="nav-center">
        <a href="{{ url_for('dashboard.dashboard') }}">Dashboard</a>
        <a href="{{ url_for('rondas.historico') }}">Histórico</a>
        <a href="{{ url_for('rondas.monitores') }}">Monitores</a>
        <a href="{{ url_for('whatsapp.monitor_whatsapp') }}">WhatsApp</a>
        <div class="nav-sep"></div>
        <a href="{{ url_for('alarmes.central_alarmes') }}">🚨 Alarmes</a>
        <a href="/ronda-loop" id="nav-loop-link" style="position:relative; display:inline-flex; align-items:center; gap:6px;">
            🔄 Loop
            <span id="nav-loop-dot"></span>
        </a>
        <a href="{{ url_for('nvr.nvr_listar') }}">📷 PTZ</a>
        <a href="{{ url_for('conferencia.painel') }}">🛰️ Conferência</a>
        <div class="nav-sep"></div>
        <a href="/email">✉️ E-mail</a>
    </div>

    <div class="nav-user">
        <div class="nav-user-info">
            <strong>{{ session.monitor_nome }}</strong>
            {{ session.monitor_turno }}
        </div>
        <a href="{{ url_for('auth.logout') }}" class="btn-logout">Sair</a>
    </div>
</nav>
{% endif %}

<div class="container">
    {% for category, message in get_flashed_messages(with_categories=true) %}
    <div class="alert alert-{{ category }}">{{ message }}</div>
    {% endfor %}

    {% block content %}{% endblock %}
</div>

{% if session.monitor_id %}
<script>
// Loop status indicator
(function() {
    function checarLoop() {
        fetch('/api/ronda-loop/status')
            .then(r => r.json())
            .then(s => {
                const dot = document.getElementById('nav-loop-dot');
                if (dot) dot.style.display = s.ativo ? 'inline-block' : 'none';
            }).catch(() => {});
    }
    checarLoop();
    setInterval(checarLoop, 10000);

    // Highlight active nav link
    const links = document.querySelectorAll('.nav-center a');
    links.forEach(a => {
        if (a.href === window.location.href ||
            (a.getAttribute('href') !== '/' && window.location.pathname.startsWith(a.getAttribute('href')))) {
            a.classList.add('active');
        }
    });
})();

// Email modal for historico page
(function() {
    if (!window.location.pathname.includes('/historico')) return;
    const modal = document.createElement('div');
    modal.id = 'email-modal';
    modal.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);backdrop-filter:blur(4px);z-index:8000;align-items:center;justify-content:center;padding:1.5rem;';
    modal.innerHTML = `
      <div style="background:var(--bg-2);border:1px solid var(--border);border-top:2px solid var(--gold);border-radius:16px;width:100%;max-width:480px;box-shadow:0 24px 64px rgba(0,0,0,.6);overflow:hidden;">
        <div style="background:var(--bg-3);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);">
          <span style="font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text);">✉️ Enviar Relatório</span>
          <button onclick="document.getElementById('email-modal').style.display='none'" style="background:none;border:none;color:var(--text-3);font-size:20px;cursor:pointer;line-height:1;">✕</button>
        </div>
        <div style="padding:20px;display:flex;flex-direction:column;gap:14px;">
          <div>
            <label style="display:block;font-size:11px;font-weight:700;color:var(--text-3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">ID da Ronda</label>
            <input id="em-ronda-id" type="number" min="1" style="width:100%;padding:9px 13px;background:var(--bg-3);border:1px solid var(--border);border-radius:8px;font-size:13px;font-family:'DM Sans',sans-serif;color:var(--text);">
          </div>
          <div>
            <label style="display:block;font-size:11px;font-weight:700;color:var(--text-3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">Destinatários <span style="text-transform:none;font-weight:400;">(separados por vírgula)</span></label>
            <input id="em-destinatarios" type="text" placeholder="supervisor@empresa.com, gerente@empresa.com" style="width:100%;padding:9px 13px;background:var(--bg-3);border:1px solid var(--border);border-radius:8px;font-size:13px;font-family:'DM Sans',sans-serif;color:var(--text);">
          </div>
          <div id="em-resultado" style="display:none;font-size:13px;padding:10px 14px;border-radius:8px;"></div>
          <div style="display:flex;gap:10px;">
            <button onclick="emailPreview()" style="flex:1;padding:9px;background:transparent;color:var(--text-2);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:13px;font-family:'DM Sans',sans-serif;font-weight:600;transition:all .15s;" onmouseover="this.style.background='var(--bg-3)'" onmouseout="this.style.background='transparent'">👁 Preview</button>
            <button onclick="emailEnviar()" style="flex:1;padding:9px;background:var(--gold);color:#111;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-family:'DM Sans',sans-serif;font-weight:700;transition:all .15s;" onmouseover="this.style.background='#ffd633'" onmouseout="this.style.background='var(--gold)'">📧 Enviar</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(modal);

    window.emailPreview = function() {
        const id = document.getElementById('em-ronda-id').value;
        if (!id) { rondaToast('Informe o ID da ronda.', 'error'); return; }
        window.open('/api/email/preview/' + id, '_blank');
    };
    window.emailEnviar = async function() {
        const id = document.getElementById('em-ronda-id').value;
        const dest = document.getElementById('em-destinatarios').value;
        if (!id || !dest) { rondaToast('Preencha todos os campos.', 'error'); return; }
        const destinatarios = dest.split(',').map(s => s.trim()).filter(Boolean);
        const el = document.getElementById('em-resultado');
        el.style.display = 'block';
        el.style.cssText += 'background:var(--bg-3);color:var(--text-2);border:1px solid var(--border);';
        el.textContent = 'Enviando...';
        try {
            const r = await fetch('/api/email/enviar-relatorio', {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ronda_id: parseInt(id), destinatarios}),
            }).then(r => r.json());
            if (r.ok) {
                el.style.cssText = el.style.cssText.replace('color:var(--text-2)', 'color:var(--green)');
                el.textContent = '✅ Relatório enviado com sucesso!';
            } else {
                el.style.cssText = el.style.cssText.replace('color:var(--text-2)', 'color:var(--red)');
                el.textContent = '❌ ' + (r.erro || 'Erro desconhecido');
            }
        } catch(e) { el.textContent = '❌ Erro: ' + e.message; }
    };

    const btn = document.createElement('button');
    btn.textContent = '✉️ Enviar por E-mail';
    btn.style.cssText = 'position:fixed;bottom:28px;right:28px;background:var(--gold);color:#111;border:none;padding:11px 20px;border-radius:8px;font-weight:700;font-size:13px;font-family:"DM Sans",sans-serif;cursor:pointer;box-shadow:0 4px 20px rgba(245,196,0,0.3);z-index:500;transition:all .15s;';
    btn.onmouseover = () => { btn.style.background = '#ffd633'; btn.style.transform = 'translateY(-2px)'; };
    btn.onmouseout  = () => { btn.style.background = 'var(--gold)'; btn.style.transform = ''; };
    btn.onclick = () => {
        document.getElementById('em-resultado').style.display = 'none';
        document.getElementById('email-modal').style.display = 'flex';
    };
    document.body.appendChild(btn);
})();

function rondaToast(msg, tipo) {
    let ct = document.getElementById('ronda-toast-ct');
    if (!ct) {
        ct = document.createElement('div');
        ct.id = 'ronda-toast-ct';
        ct.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;gap:8px;z-index:9000;';
        document.body.appendChild(ct);
    }
    const el = document.createElement('div');
    const bg  = tipo === 'ok' ? 'rgba(34,197,94,0.15)'    : 'rgba(232,64,87,0.15)';
    const bdr = tipo === 'ok' ? 'rgba(34,197,94,0.4)'     : 'rgba(232,64,87,0.4)';
    const col = tipo === 'ok' ? 'var(--green)'             : 'var(--red)';
    el.style.cssText = `font-size:13px;padding:11px 18px;border-radius:8px;background:${bg};border:1px solid ${bdr};color:${col};font-family:'DM Sans',sans-serif;font-weight:500;white-space:nowrap;box-shadow:0 8px 32px rgba(0,0,0,.4);`;
    el.textContent = msg;
    ct.appendChild(el);
    setTimeout(() => el.remove(), 3500);
}
</script>
{% endif %}

{% block extra_js %}{% endblock %}

</body>
</html>

{% extends "base.html" %}
{% block title %}Dashboard — Grupo Ronda{% endblock %}

{% block content %}

<div class="page-header">
    <h1>Dashboard</h1>
    <div style="display:flex; gap:10px; align-items:center;">
        <select onchange="location.href='/dashboard?dias='+this.value"
                style="padding:6px 12px; border:1px solid #2a2a2a; border-radius:7px;
                       background:#181818; color:#888; font-size:12px; cursor:pointer; outline:none;">
            <option value="7"  {% if dias==7  %}selected{% endif %}>7 dias</option>
            <option value="15" {% if dias==15 %}selected{% endif %}>15 dias</option>
            <option value="30" {% if dias==30 %}selected{% endif %}>30 dias</option>
            <option value="90" {% if dias==90 %}selected{% endif %}>90 dias</option>
        </select>
        <form method="POST" action="{{ url_for('rondas.iniciar_ronda_multi') }}" style="margin:0;">
            <button type="submit" class="btn btn-success" style="font-size:13px; padding:7px 18px;">
                Iniciar Ronda
            </button>
        </form>
    </div>
</div>

<!-- CARD MONITOR -->
<div style="background:#0a0a0a; border:1px solid #1e1e1e; border-left:3px solid #f5c400;
            border-radius:10px; padding:1rem 1.5rem; margin-bottom:1.5rem;
            display:flex; align-items:center; justify-content:space-between;">
    <div style="display:flex; align-items:center; gap:14px;">
        <div style="width:40px; height:40px; border-radius:50%; background:#f5c400;
                    display:flex; align-items:center; justify-content:center;
                    font-size:16px; font-weight:700; color:#111; flex-shrink:0;">
            {{ session.monitor_nome[0] | upper }}
        </div>
        <div>
            <div style="font-size:14px; font-weight:700; color:#fff;">{{ session.monitor_nome }}</div>
            <div style="font-size:11px; color:#555; margin-top:1px;">{{ session.monitor_turno }}</div>
        </div>
    </div>
    <div style="text-align:right;">
        <div style="font-size:10px; color:#444; text-transform:uppercase; letter-spacing:.06em;">Ultimo acesso</div>
        <div style="font-size:12px; color:#f5c400; margin-top:2px;" id="hora-atual"></div>
    </div>
</div>

<!-- SECAO: RONDAS -->
<div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:#444;
            text-transform:uppercase; margin-bottom:.75rem; padding-left:2px;">Rondas</div>

<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:1px;
            background:#1a1a1a; border-radius:10px; overflow:hidden; margin-bottom:1.5rem;">

    <div style="background:#0d0d0d; padding:1.25rem 1.5rem;">
        <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555; margin-bottom:.75rem;">REALIZADAS</div>
        <div style="font-size:34px; font-weight:700; color:#e0e0e0; line-height:1;">{{ kpi.rondas_total }}</div>
        <div style="font-size:11px; color:#444; margin-top:.5rem;">{{ kpi.rondas_hoje }} hoje</div>
    </div>

    <div style="background:#0d0d0d; padding:1.25rem 1.5rem; border-left:1px solid #1a1a1a;">
        <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555; margin-bottom:.75rem;">CONCLUIDAS</div>
        <div style="font-size:34px; font-weight:700; color:#6ee7a0; line-height:1;">{{ kpi.rondas_ok }}</div>
        <div style="font-size:11px; color:#444; margin-top:.5rem;">sem ocorrencias</div>
    </div>

    <div style="background:#0d0d0d; padding:1.25rem 1.5rem; border-left:1px solid #1a1a1a;">
        <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555; margin-bottom:.75rem;">COM ALERTAS</div>
        <div style="font-size:34px; font-weight:700; color:#f87171; line-height:1;">{{ kpi.rondas_alerta }}</div>
        <div style="font-size:11px; color:#444; margin-top:.5rem;">deteccoes registradas</div>
    </div>

    <div style="background:#0d0d0d; padding:1.25rem 1.5rem; border-left:1px solid #1a1a1a;">
        <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555; margin-bottom:.75rem;">DURACAO MEDIA</div>
        <div style="font-size:34px; font-weight:700; color:#7dd3fc; line-height:1;">
            {{ kpi.tempo_medio_min }}<span style="font-size:14px; color:#555; margin-left:2px;">min</span>
        </div>
        <div style="font-size:11px; color:#444; margin-top:.5rem;">por ciclo</div>
    </div>
</div>

<!-- SECAO: DETECCOES -->
<div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:#444;
            text-transform:uppercase; margin-bottom:.75rem; padding-left:2px;">Detecções</div>

<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:1px;
            background:#1a1a1a; border-radius:10px; overflow:hidden; margin-bottom:1.5rem;">

    <div style="background:#0d0d0d; padding:1.25rem 1.5rem;">
        <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555; margin-bottom:.75rem;">TOTAL</div>
        <div style="font-size:34px; font-weight:700; color:#e0e0e0; line-height:1;">{{ kpi.det_total }}</div>
        <div style="font-size:11px; color:#444; margin-top:.5rem;">no periodo</div>
    </div>

    <div style="background:#0d0d0d; padding:1.25rem 1.5rem; border-left:1px solid #1a1a1a;">
        <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555; margin-bottom:.75rem;">PENDENTES</div>
        <div style="font-size:34px; font-weight:700; color:#f5c400; line-height:1;">{{ kpi.det_pendente }}</div>
        <div style="font-size:11px; color:#444; margin-top:.5rem;">sem tratativa</div>
    </div>

    <div style="background:#0d0d0d; padding:1.25rem 1.5rem; border-left:1px solid #1a1a1a;">
        <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555; margin-bottom:.75rem;">DETECÇÕES FALSAS</div>
        <div style="font-size:34px; font-weight:700; color:#f87171; line-height:1;">{{ kpi.det_tratando }}</div>
        <div style="font-size:11px; color:#444; margin-top:.5rem;">descartadas</div>
    </div>

    <div style="background:#0d0d0d; padding:1.25rem 1.5rem; border-left:1px solid #1a1a1a;">
        <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555; margin-bottom:.75rem;">TRATADOS</div>
        <div style="font-size:34px; font-weight:700; color:#6ee7a0; line-height:1;">{{ kpi.det_tratado }}</div>
        <div style="font-size:11px; color:#444; margin-top:.5rem;">com tratativa</div>
    </div>
</div>

<!-- SECAO: QUALIDADE + GRAFICO -->
<div style="display:grid; grid-template-columns:1fr 1.6fr; gap:1rem; margin-bottom:1.5rem;">

    <!-- Qualidade do modelo -->
    <div>
        <div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:#444;
                    text-transform:uppercase; margin-bottom:.75rem; padding-left:2px;">Qualidade do Modelo</div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1px; background:#1a1a1a;
                    border-radius:10px; overflow:hidden; margin-bottom:1px;">
            <div style="background:#0d0d0d; padding:1.25rem 1.5rem;">
                <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555; margin-bottom:.75rem;">CONFIRMADOS</div>
                <div style="font-size:34px; font-weight:700; color:#6ee7a0; line-height:1;">{{ kpi.confirmados }}</div>
                <div style="font-size:11px; color:#444; margin-top:.5rem;">invasoes reais</div>
            </div>
            <div style="background:#0d0d0d; padding:1.25rem 1.5rem; border-left:1px solid #1a1a1a;">
                <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555; margin-bottom:.75rem;">DETECÇÕES FALSAS</div>
                <div style="font-size:34px; font-weight:700; color:#f87171; line-height:1;">{{ kpi.falsos_positivos }}</div>
                <div style="font-size:11px; color:#444; margin-top:.5rem;">descartados</div>
            </div>
        </div>

        <!-- Precisao -->
        <div style="background:#0d0d0d; border:1px solid #1a1a1a; border-radius:10px;
                    padding:1.25rem 1.5rem; margin-top:1px;">
            <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:.75rem;">
                <div style="font-size:10px; font-weight:700; letter-spacing:.08em; color:#555;">PRECISAO DO MODELO</div>
                <div style="font-size:24px; font-weight:700;
                            color:{% if kpi.precisao >= 80 %}#6ee7a0{% elif kpi.precisao >= 60 %}#f5c400{% else %}#f87171{% endif %};">
                    {{ kpi.precisao }}<span style="font-size:13px;">%</span>
                </div>
            </div>
            <div style="background:#1a1a1a; border-radius:4px; height:5px; overflow:hidden;">
                <div style="height:100%; border-radius:4px; transition:width .5s;
                            width:{{ kpi.precisao }}%;
                            background:{% if kpi.precisao >= 80 %}#6ee7a0{% elif kpi.precisao >= 60 %}#f5c400{% else %}#f87171{% endif %};"></div>
            </div>
            <div style="font-size:10px; color:#444; margin-top:.5rem;">confirmados / total</div>
        </div>
    </div>

    <!-- Grafico deteccoes por dia -->
    <div>
        <div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:#444;
                    text-transform:uppercase; margin-bottom:.75rem; padding-left:2px;">Deteccoes por Dia — ultimos 14 dias</div>
        <div style="background:#0d0d0d; border:1px solid #1a1a1a; border-radius:10px;
                    padding:1.25rem 1.5rem; height:calc(100% - 26px);">
            <canvas id="chart-det" style="width:100%; height:180px;"></canvas>
        </div>
    </div>
</div>

<!-- SECAO: NVRs + RONDAS RECENTES -->
<div style="display:grid; grid-template-columns:1fr 2fr; gap:1rem; margin-bottom:1.5rem;">

    <!-- Top NVRs -->
    <div>
        <div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:#444;
                    text-transform:uppercase; margin-bottom:.75rem; padding-left:2px;">
            Alertas por NVR — top {{ kpi.top_nvrs|length }}
        </div>
        <div style="background:#0d0d0d; border:1px solid #1a1a1a; border-radius:10px; padding:1.25rem 1.5rem;">
            {% if kpi.top_nvrs %}
                {% for nvr in kpi.top_nvrs %}
                <div style="margin-bottom:{% if not loop.last %}1rem{% else %}0{% endif %};">
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <span style="font-size:12px; color:#aaa;">{{ nvr.nome }}</span>
                        <span style="font-size:12px; font-weight:700; color:#f5c400;">{{ nvr.total }}</span>
                    </div>
                    <div style="background:#1a1a1a; border-radius:3px; height:4px; overflow:hidden;">
                        <div style="background:#f5c400; height:100%; width:{{ nvr.pct }}%; border-radius:3px;"></div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p style="color:#444; font-size:12px; text-align:center; padding:1rem 0;">Nenhum dado.</p>
            {% endif %}
        </div>
    </div>

    <!-- Rondas recentes -->
    <div>
        <div style="font-size:10px; font-weight:700; letter-spacing:.1em; color:#444;
                    text-transform:uppercase; margin-bottom:.75rem; padding-left:2px;">
            Ultimas Rondas
        </div>
        <div style="background:#0d0d0d; border:1px solid #1a1a1a; border-radius:10px; overflow:hidden;">
            {% if rondas %}
            <table style="font-size:13px;">
                <thead>
                    <tr>
                        <th style="background:#0d0d0d; padding:10px 16px; font-size:10px; letter-spacing:.08em; color:#444; font-weight:700; border-bottom:1px solid #1a1a1a;">#</th>
                        <th style="background:#0d0d0d; padding:10px 16px; font-size:10px; letter-spacing:.08em; color:#444; font-weight:700; border-bottom:1px solid #1a1a1a;">Monitor</th>
                        <th style="background:#0d0d0d; padding:10px 16px; font-size:10px; letter-spacing:.08em; color:#444; font-weight:700; border-bottom:1px solid #1a1a1a;">Inicio</th>
                        <th style="background:#0d0d0d; padding:10px 16px; font-size:10px; letter-spacing:.08em; color:#444; font-weight:700; border-bottom:1px solid #1a1a1a;">Fim</th>
                        <th style="background:#0d0d0d; padding:10px 16px; font-size:10px; letter-spacing:.08em; color:#444; font-weight:700; border-bottom:1px solid #1a1a1a;">Status</th>
                        <th style="background:#0d0d0d; padding:10px 16px; font-size:10px; letter-spacing:.08em; color:#444; font-weight:700; border-bottom:1px solid #1a1a1a;"></th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in rondas[:5] %}
                    <tr style="border-bottom:{% if not loop.last %}1px solid #141414{% else %}none{% endif %};">
                        <td style="padding:12px 16px; color:#444; font-size:11px;">{{ r.id }}</td>
                        <td style="padding:12px 16px; color:#ccc; font-weight:600;">{{ r.monitor_nome }}</td>
                        <td style="padding:12px 16px; color:#666; font-size:12px; white-space:nowrap;">{{ r.iniciada_em.strftime('%Y-%m-%d %H:%M') if r.iniciada_em else '' }}</td>
                        <td style="padding:12px 16px; color:#666; font-size:12px; white-space:nowrap;">{{ r.finalizada_em.strftime('%Y-%m-%d %H:%M') if r.finalizada_em else '—' }}</td>
                        <td style="padding:12px 16px;">
                            {% if r.status == 'finalizada' %}
                                <span style="font-size:10px; font-weight:700; letter-spacing:.05em;
                                             color:#6ee7a0; background:rgba(110,231,160,.1);
                                             padding:3px 8px; border-radius:4px;">FINALIZADA</span>
                            {% elif r.status == 'com_alertas' %}
                                <span style="font-size:10px; font-weight:700; letter-spacing:.05em;
                                             color:#f87171; background:rgba(248,113,113,.1);
                                             padding:3px 8px; border-radius:4px;">COM ALERTAS</span>
                            {% elif r.status == 'em_andamento' %}
                                <span style="font-size:10px; font-weight:700; letter-spacing:.05em;
                                             color:#f5c400; background:rgba(245,196,0,.1);
                                             padding:3px 8px; border-radius:4px;">EM ANDAMENTO</span>
                            {% else %}
                                <span style="font-size:10px; font-weight:700; letter-spacing:.05em;
                                             color:#555; background:rgba(85,85,85,.1);
                                             padding:3px 8px; border-radius:4px;">{{ r.status | upper }}</span>
                            {% endif %}
                        </td>
                        <td style="padding:12px 16px;">
                            {% if r.status != 'em_andamento' %}
                            <a href="{{ url_for('rondas.ver_relatorio_multi', ronda_id=r.id) }}"
                               style="font-size:11px; font-weight:700; color:#f5c400; text-decoration:none;
                                      padding:4px 10px; border:1px solid rgba(245,196,0,.3);
                                      border-radius:5px; transition:background .15s;"
                               onmouseover="this.style.background='rgba(245,196,0,.1)'"
                               onmouseout="this.style.background='transparent'">Ver</a>
                            {% else %}
                            <span style="font-size:11px; color:#333;">—</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p style="color:#444; font-size:13px; text-align:center; padding:2rem;">Nenhuma ronda registrada.</p>
            {% endif %}
            <div style="padding:10px 16px; border-top:1px solid #141414; text-align:right;">
                <a href="{{ url_for('rondas.historico') }}"
                   style="font-size:11px; color:#555; text-decoration:none; letter-spacing:.04em;">
                    Ver historico completo &rarr;
                </a>
            </div>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
function atualizarHora() {
    const el = document.getElementById('hora-atual');
    if (el) el.textContent = new Date().toLocaleString('pt-BR');
}
atualizarHora();
setInterval(atualizarHora, 1000);

new Chart(document.getElementById('chart-det'), {
    type: 'bar',
    data: {
        labels: {{ kpi.grafico_labels | tojson }},
        datasets: [{
            data: {{ kpi.grafico_valores | tojson }},
            backgroundColor: 'rgba(245,196,0,0.15)',
            borderColor: 'rgba(245,196,0,0.6)',
            borderWidth: 1,
            borderRadius: 3,
            hoverBackgroundColor: 'rgba(245,196,0,0.3)',
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: '#111',
                titleColor: '#f5c400',
                bodyColor: '#888',
                borderColor: '#222',
                borderWidth: 1,
                callbacks: { title: i => i[0].label, label: i => ' ' + i.raw + ' deteccao(es)' }
            }
        },
        scales: {
            x: { ticks: { color: '#444', font: { size: 10 } }, grid: { color: '#141414' } },
            y: { beginAtZero: true, ticks: { color: '#444', stepSize: 1, font: { size: 10 } }, grid: { color: '#141414' } }
        }
    }
});
</script>

{% endblock %}

{% extends "base.html" %}
{% block title %}Envio de Relatórios por E-mail — Grupo Ronda{% endblock %}

{% block content %}
<div class="page-header">
    <h1>📧 Envio de Relatórios por E-mail</h1>
</div>

<div style="display:grid; grid-template-columns:340px 1fr; gap:1.5rem; align-items:start;">

    <!-- FILTROS -->
    <div class="card" style="position:sticky; top:1rem;">
        <div class="card-title">🔍 Filtrar Relatórios</div>

        <div class="form-group">
            <label>Período</label>
            <select id="f-periodo" onchange="ajustarPeriodo()">
                <option value="hoje">Hoje</option>
                <option value="7d">Últimos 7 dias</option>
                <option value="30d">Últimos 30 dias</option>
                <option value="custom">Personalizado</option>
            </select>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <div class="form-group">
                <label>De</label>
                <input type="date" id="f-data-ini">
            </div>
            <div class="form-group">
                <label>Até</label>
                <input type="date" id="f-data-fim">
            </div>
        </div>

        <div class="form-group">
            <label>Turno</label>
            <select id="f-turno">
                <option value="">Todos os turnos</option>
                <option value="Diurno">Diurno</option>
                <option value="Noturno">Noturno</option>
                <option value="Administrativo">Administrativo</option>
            </select>
        </div>

        <div class="form-group">
            <label>Monitor</label>
            <select id="f-monitor">
                <option value="">Todos os monitores</option>
                {% for m in monitores %}
                <option value="{{ m.nome }}">{{ m.nome }}</option>
                {% endfor %}
            </select>
        </div>

        <div class="form-group">
            <label>Status da Ronda</label>
            <select id="f-status">
                <option value="">Todos</option>
                <option value="finalizado">Finalizado</option>
                <option value="em_andamento">Em andamento</option>
                <option value="erro">Com erro</option>
            </select>
        </div>

        <button onclick="buscarRondas()" class="btn btn-primary" style="width:100%; margin-top:4px;">
            🔍 Buscar Relatórios
        </button>
        <button onclick="limparFiltros()" class="btn" style="width:100%; margin-top:8px; background:transparent; border:1px solid #444; color:#aaa;">
            ✕ Limpar filtros
        </button>

        <hr style="margin:1.2rem 0; border:none; border-top:1px solid #333;">

        <!-- DESTINATÁRIOS -->
        <div class="card-title" style="margin-bottom:.8rem;">📬 Destinatários</div>
        <div class="form-group">
            <label>E-mails <small style="color:#aaa; text-transform:none;">(separados por vírgula)</small></label>
            <textarea id="email-destinatarios" rows="3"
                style="width:100%; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
                border-radius:8px; color:#fff; font-size:13px; padding:10px; resize:vertical; font-family:inherit;"
                placeholder="supervisor@empresa.com,&#10;gerente@empresa.com"></textarea>
        </div>

        <div id="sel-count" style="font-size:12px; color:#aaa; margin-bottom:10px; min-height:18px;"></div>

        <button onclick="enviarSelecionados()" class="btn btn-success" style="width:100%;">
            📤 Enviar Selecionados
        </button>

        <div id="resultado-envio" style="display:none; margin-top:10px; font-size:13px; padding:10px 14px;
             border-radius:8px; border-left:4px solid;"></div>
    </div>

    <!-- TABELA DE RESULTADOS -->
    <div class="card" style="padding:0; overflow:hidden;">
        <div style="padding:16px 20px; border-bottom:1px solid rgba(255,255,255,0.07);
             display:flex; align-items:center; justify-content:space-between;">
            <div class="card-title" style="margin:0;">📋 Relatórios Encontrados</div>
            <div style="display:flex; align-items:center; gap:10px;">
                <label style="display:flex; align-items:center; gap:6px; font-size:12px; color:#aaa; cursor:pointer; text-transform:none; letter-spacing:0;">
                    <input type="checkbox" id="chk-all" onchange="toggleTodos(this)"
                           style="accent-color:var(--gold); width:14px; height:14px;">
                    Selecionar todos
                </label>
                <span id="total-label" style="font-size:12px; color:#aaa;"></span>
            </div>
        </div>

        <div id="tabela-wrap">
            <div id="estado-inicial" style="padding:60px 20px; text-align:center; color:#555;">
                <div style="font-size:36px; margin-bottom:12px; opacity:.4;">📂</div>
                <p style="font-size:14px;">Use os filtros ao lado para buscar relatórios.</p>
            </div>
        </div>
    </div>

</div>

<!-- MODAL PREVIEW -->
<div id="preview-overlay" style="display:none; position:fixed; inset:0;
     background:rgba(0,0,0,0.8); z-index:8000; align-items:center; justify-content:center;">
    <div style="background:#fff; width:92%; max-width:980px; height:88vh;
         border-radius:10px; overflow:hidden; display:flex; flex-direction:column;
         box-shadow:0 24px 60px rgba(0,0,0,.6);">
        <div style="background:#111; padding:12px 18px; display:flex;
             justify-content:space-between; align-items:center; gap:12px;">
            <span style="color:#fff; font-weight:700; font-size:14px;" id="preview-titulo">👁 Preview do Relatório</span>
            <div style="display:flex; gap:8px;">
                <button onclick="enviarPreviewAtual()"
                    style="height:32px; padding:0 14px; background:var(--gold); border:none; border-radius:6px;
                    color:#111; font-size:13px; font-weight:700; cursor:pointer;">
                    📤 Enviar este
                </button>
                <button onclick="fecharPreview()"
                    style="background:none; border:1px solid #444; color:#aaa; border-radius:6px;
                    padding:0 12px; height:32px; font-size:13px; cursor:pointer;">✕ Fechar</button>
            </div>
        </div>
        <iframe id="preview-frame" style="flex:1; border:none; width:100%;"></iframe>
    </div>
</div>

<style>
.ronda-row {
    display:grid;
    grid-template-columns:36px 60px 1fr 120px 110px 100px 130px;
    align-items:center;
    gap:10px;
    padding:11px 20px;
    border-bottom:1px solid rgba(255,255,255,0.05);
    transition:background .12s;
    font-size:13px;
}
.ronda-row:hover { background:rgba(255,255,255,0.03); }
.ronda-row.selected { background:rgba(245,196,0,0.06); }
.ronda-header {
    background:rgba(255,255,255,0.03);
    font-size:11px;
    font-weight:700;
    color:#666;
    text-transform:uppercase;
    letter-spacing:.06em;
    border-bottom:1px solid rgba(255,255,255,0.08);
}
.badge-status {
    display:inline-block; padding:2px 8px; border-radius:20px;
    font-size:11px; font-weight:600; white-space:nowrap;
}
.st-fin  { background:rgba(25,135,84,.15);  color:#28a745; border:1px solid rgba(25,135,84,.3); }
.st-and  { background:rgba(13,110,253,.12); color:#4d9cf5; border:1px solid rgba(13,110,253,.3); }
.st-err  { background:rgba(220,53,69,.12);  color:#dc3545; border:1px solid rgba(220,53,69,.3); }
.btn-row {
    height:26px; padding:0 10px; border-radius:5px; border:1px solid rgba(255,255,255,0.12);
    background:rgba(255,255,255,0.05); color:#ccc; font-size:11px; cursor:pointer;
    display:inline-flex; align-items:center; gap:4px; transition:all .15s; white-space:nowrap;
}
.btn-row:hover { border-color:var(--gold); color:var(--gold); }
.btn-row.enviar:hover { border-color:#28a745; color:#28a745; }
</style>

<script>
let rondasEncontradas = [];
let previewAtualId = null;

document.addEventListener('DOMContentLoaded', () => {
    ajustarPeriodo();
    buscarRondas();
});

function ajustarPeriodo() {
    const v = document.getElementById('f-periodo').value;
    const hoje = new Date(), fmt = d => d.toISOString().slice(0,10);
    const ini = document.getElementById('f-data-ini');
    const fim = document.getElementById('f-data-fim');
    fim.value = fmt(hoje);
    if (v === 'hoje') ini.value = fmt(hoje);
    else if (v === '7d') { const d = new Date(hoje); d.setDate(d.getDate()-6); ini.value = fmt(d); }
    else if (v === '30d') { const d = new Date(hoje); d.setDate(d.getDate()-29); ini.value = fmt(d); }
    ini.disabled = fim.disabled = (v !== 'custom');
}

function limparFiltros() {
    document.getElementById('f-turno').value = '';
    document.getElementById('f-monitor').value = '';
    document.getElementById('f-status').value = '';
    document.getElementById('f-periodo').value = 'hoje';
    ajustarPeriodo();
    buscarRondas();
}

async function buscarRondas() {
    const params = new URLSearchParams({
        data_ini:  document.getElementById('f-data-ini').value,
        data_fim:  document.getElementById('f-data-fim').value,
        turno:     document.getElementById('f-turno').value,
        monitor:   document.getElementById('f-monitor').value,
        status:    document.getElementById('f-status').value,
    });

    const wrap = document.getElementById('tabela-wrap');
    wrap.innerHTML = '<div style="padding:40px; text-align:center; color:#555; font-size:13px;">⏳ Buscando...</div>';

    try {
        const r = await fetch('/api/email/rondas?' + params);
        const d = await r.json();
        rondasEncontradas = d.rondas || [];
        renderTabela(rondasEncontradas);
    } catch(e) {
        wrap.innerHTML = `<div style="padding:40px; text-align:center; color:#dc3545; font-size:13px;">❌ Erro: ${e.message}</div>`;
    }
}

function renderTabela(rondas) {
    const wrap = document.getElementById('tabela-wrap');
    document.getElementById('total-label').textContent = `${rondas.length} registro(s)`;
    document.getElementById('chk-all').checked = false;
    atualizarContador();

    if (!rondas.length) {
        wrap.innerHTML = '<div style="padding:60px 20px; text-align:center; color:#555;"><div style="font-size:36px;margin-bottom:12px;opacity:.4;">🔍</div><p style="font-size:14px;">Nenhum relatório encontrado com os filtros aplicados.</p></div>';
        return;
    }

    const stMap = {
        finalizado:   ['st-fin', '✅ Finalizado'],
        em_andamento: ['st-and', '⏳ Em andamento'],
        erro:         ['st-err', '❌ Com erro'],
    };

    let html = `
    <div class="ronda-row ronda-header">
        <span></span>
        <span>ID</span>
        <span>Monitor / Turno</span>
        <span>Data/Hora</span>
        <span>Status</span>
        <span>Duração</span>
        <span>Ações</span>
    </div>`;

    rondas.forEach(r => {
        const [sc, sl] = stMap[r.status] || ['st-err', r.status];
        const hora = r.iniciada_em ? r.iniciada_em.slice(0,16).replace('T',' ') : '—';
        const dur = calcDuracao(r.iniciada_em, r.finalizada_em);
        html += `
        <div class="ronda-row" id="row-${r.id}" onclick="toggleRow(${r.id})">
            <div onclick="event.stopPropagation()">
                <input type="checkbox" class="row-chk" data-id="${r.id}"
                    style="accent-color:var(--gold); width:14px; height:14px;"
                    onchange="atualizarContador()">
            </div>
            <span style="font-family:monospace; color:#aaa;">#${r.id}</span>
            <div>
                <div style="font-weight:600; color:#e0e0e0;">${r.monitor_nome}</div>
                <div style="font-size:11px; color:#666; margin-top:2px;">🕐 ${r.turno}</div>
            </div>
            <span style="font-size:12px; color:#bbb;">${hora}</span>
            <span><span class="badge-status ${sc}">${sl}</span></span>
            <span style="font-size:12px; color:#888;">${dur}</span>
            <div style="display:flex; gap:5px;" onclick="event.stopPropagation()">
                <button class="btn-row" onclick="verPreview(${r.id}, '${r.monitor_nome} #${r.id}')">👁 Ver</button>
                <button class="btn-row enviar" onclick="enviarUnico(${r.id})">📤 Enviar</button>
            </div>
        </div>`;
    });

    wrap.innerHTML = html;
}

function calcDuracao(ini, fim) {
    if (!ini || !fim) return '—';
    try {
        const diff = Math.floor((new Date(fim) - new Date(ini)) / 1000);
        const h = Math.floor(diff / 3600), m = Math.floor((diff % 3600) / 60);
        return h > 0 ? `${h}h ${m}min` : `${m}min`;
    } catch { return '—'; }
}

function toggleRow(id) {
    const chk = document.querySelector(`.row-chk[data-id="${id}"]`);
    if (chk) { chk.checked = !chk.checked; atualizarContador(); }
    const row = document.getElementById(`row-${id}`);
    if (row) row.classList.toggle('selected', chk.checked);
}

function toggleTodos(el) {
    document.querySelectorAll('.row-chk').forEach(c => {
        c.checked = el.checked;
        const row = document.getElementById(`row-${c.dataset.id}`);
        if (row) row.classList.toggle('selected', el.checked);
    });
    atualizarContador();
}

function atualizarContador() {
    const n = document.querySelectorAll('.row-chk:checked').length;
    document.getElementById('sel-count').textContent =
        n > 0 ? `✅ ${n} relatório(s) selecionado(s)` : '';
}

function getSelecionados() {
    return [...document.querySelectorAll('.row-chk:checked')].map(c => parseInt(c.dataset.id));
}

function getDestinatarios() {
    return document.getElementById('email-destinatarios').value
        .split(/[,\n]/).map(s => s.trim()).filter(Boolean);
}

async function enviarUnico(id) {
    const dests = getDestinatarios();
    if (!dests.length) { toast('Informe ao menos um destinatário.', 'error'); return; }
    await enviarRelatorios([id], dests);
}

async function enviarSelecionados() {
    const ids = getSelecionados();
    if (!ids.length) { toast('Selecione ao menos um relatório.', 'error'); return; }
    const dests = getDestinatarios();
    if (!dests.length) { toast('Informe ao menos um destinatário.', 'error'); return; }
    await enviarRelatorios(ids, dests);
}

async function enviarRelatorios(ids, destinatarios) {
    const el = document.getElementById('resultado-envio');
    el.style.display = 'block';
    el.style.borderColor = '#555';
    el.style.color = '#aaa';
    el.innerHTML = `⏳ Enviando ${ids.length} relatório(s)...`;

    let ok = 0, erros = [];
    for (const id of ids) {
        try {
            const r = await fetch('/api/email/enviar-relatorio', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ronda_id: id, destinatarios}),
            }).then(r => r.json());
            if (r.ok) ok++; else erros.push(`#${id}: ${r.erro}`);
        } catch(e) { erros.push(`#${id}: ${e.message}`); }
    }

    if (!erros.length) {
        el.style.borderColor = '#28a745';
        el.style.color = '#28a745';
        el.innerHTML = `✅ ${ok} relatório(s) enviado(s) com sucesso!`;
        toast(`✅ ${ok} relatório(s) enviado(s)!`, 'ok');
    } else {
        el.style.borderColor = '#dc3545';
        el.style.color = '#dc3545';
        el.innerHTML = `⚠️ ${ok} enviado(s). Erros:<br>${erros.join('<br>')}`;
    }
}

function verPreview(id, titulo) {
    previewAtualId = id;
    document.getElementById('preview-titulo').textContent = `👁 Preview — ${titulo}`;
    document.getElementById('preview-frame').src = `/api/email/preview/${id}`;
    document.getElementById('preview-overlay').style.display = 'flex';
}

function fecharPreview() {
    document.getElementById('preview-overlay').style.display = 'none';
    document.getElementById('preview-frame').src = '';
    previewAtualId = null;
}

async function enviarPreviewAtual() {
    if (!previewAtualId) return;
    const dests = getDestinatarios();
    if (!dests.length) { toast('Informe destinatários no painel de filtros.', 'error'); return; }
    fecharPreview();
    await enviarRelatorios([previewAtualId], dests);
}

function toast(msg, tipo) {
    let ct = document.getElementById('toast-ct');
    if (!ct) {
        ct = document.createElement('div');
        ct.id = 'toast-ct';
        ct.style.cssText = 'position:fixed;bottom:24px;right:24px;display:flex;flex-direction:column;gap:8px;z-index:9000;';
        document.body.appendChild(ct);
    }
    const el = document.createElement('div');
    el.style.cssText = `font-size:13px;padding:12px 18px;border-radius:8px;background:#1e1e1e;
        box-shadow:0 8px 32px rgba(0,0,0,.5);
        border-left:4px solid ${tipo==='ok'?'#28a745':'#dc3545'};
        color:${tipo==='ok'?'#4ade80':'#f87171'};max-width:340px;`;
    el.textContent = msg;
    ct.appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharPreview(); });
</script>
{% endblock %}

{% extends "base.html" %}
{% block title %}Envio de Relatórios por E-mail — Grupo Ronda{% endblock %}

{% block content %}
<div class="page-header">
    <h1>📧 Envio de Relatórios por E-mail</h1>
</div>

<div style="display:grid; grid-template-columns:340px 1fr; gap:1.5rem; align-items:start;">

    <!-- FILTROS -->
    <div class="card" style="position:sticky; top:1rem;">
        <div class="card-title">🔍 Filtrar Relatórios</div>

        <div class="form-group">
            <label>Período</label>
            <select id="f-periodo" onchange="ajustarPeriodo()">
                <option value="hoje">Hoje</option>
                <option value="7d">Últimos 7 dias</option>
                <option value="30d">Últimos 30 dias</option>
                <option value="custom">Personalizado</option>
            </select>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <div class="form-group">
                <label>De</label>
                <input type="date" id="f-data-ini">
            </div>
            <div class="form-group">
                <label>Até</label>
                <input type="date" id="f-data-fim">
            </div>
        </div>

        <div class="form-group">
            <label>Turno</label>
            <select id="f-turno">
                <option value="">Todos os turnos</option>
                <option value="Diurno">Diurno</option>
                <option value="Noturno">Noturno</option>
                <option value="Administrativo">Administrativo</option>
            </select>
        </div>

        <div class="form-group">
            <label>Monitor</label>
            <select id="f-monitor">
                <option value="">Todos os monitores</option>
                {% for m in monitores %}
                <option value="{{ m.nome }}">{{ m.nome }}</option>
                {% endfor %}
            </select>
        </div>

        <div class="form-group">
            <label>Status da Ronda</label>
            <select id="f-status">
                <option value="">Todos</option>
                <option value="finalizado">Finalizado</option>
                <option value="em_andamento">Em andamento</option>
                <option value="erro">Com erro</option>
            </select>
        </div>

        <button onclick="buscarRondas()" class="btn btn-primary" style="width:100%; margin-top:4px;">
            🔍 Buscar Relatórios
        </button>
        <button onclick="limparFiltros()" class="btn" style="width:100%; margin-top:8px; background:transparent; border:1px solid #444; color:#aaa;">
            ✕ Limpar filtros
        </button>

        <hr style="margin:1.2rem 0; border:none; border-top:1px solid #333;">

        <!-- DESTINATÁRIOS -->
        <div class="card-title" style="margin-bottom:.8rem;">📬 Destinatários</div>
        <div class="form-group">
            <label>E-mails <small style="color:#aaa; text-transform:none;">(separados por vírgula)</small></label>
            <textarea id="email-destinatarios" rows="3"
                style="width:100%; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
                border-radius:8px; color:#fff; font-size:13px; padding:10px; resize:vertical; font-family:inherit;"
                placeholder="supervisor@empresa.com,&#10;gerente@empresa.com"></textarea>
        </div>

        <div id="sel-count" style="font-size:12px; color:#aaa; margin-bottom:10px; min-height:18px;"></div>

        <button onclick="enviarSelecionados()" class="btn btn-success" style="width:100%;">
            📤 Enviar Selecionados
        </button>

        <div id="resultado-envio" style="display:none; margin-top:10px; font-size:13px; padding:10px 14px;
             border-radius:8px; border-left:4px solid;"></div>
    </div>

    <!-- TABELA DE RESULTADOS -->
    <div class="card" style="padding:0; overflow:hidden;">
        <div style="padding:16px 20px; border-bottom:1px solid rgba(255,255,255,0.07);
             display:flex; align-items:center; justify-content:space-between;">
            <div class="card-title" style="margin:0;">📋 Relatórios Encontrados</div>
            <div style="display:flex; align-items:center; gap:10px;">
                <label style="display:flex; align-items:center; gap:6px; font-size:12px; color:#aaa; cursor:pointer; text-transform:none; letter-spacing:0;">
                    <input type="checkbox" id="chk-all" onchange="toggleTodos(this)"
                           style="accent-color:var(--gold); width:14px; height:14px;">
                    Selecionar todos
                </label>
                <span id="total-label" style="font-size:12px; color:#aaa;"></span>
            </div>
        </div>

        <div id="tabela-wrap">
            <div id="estado-inicial" style="padding:60px 20px; text-align:center; color:#555;">
                <div style="font-size:36px; margin-bottom:12px; opacity:.4;">📂</div>
                <p style="font-size:14px;">Use os filtros ao lado para buscar relatórios.</p>
            </div>
        </div>
    </div>

</div>

<!-- MODAL PREVIEW -->
<div id="preview-overlay" style="display:none; position:fixed; inset:0;
     background:rgba(0,0,0,0.8); z-index:8000; align-items:center; justify-content:center;">
    <div style="background:#fff; width:92%; max-width:980px; height:88vh;
         border-radius:10px; overflow:hidden; display:flex; flex-direction:column;
         box-shadow:0 24px 60px rgba(0,0,0,.6);">
        <div style="background:#111; padding:12px 18px; display:flex;
             justify-content:space-between; align-items:center; gap:12px;">
            <span style="color:#fff; font-weight:700; font-size:14px;" id="preview-titulo">👁 Preview do Relatório</span>
            <div style="display:flex; gap:8px;">
                <button onclick="enviarPreviewAtual()"
                    style="height:32px; padding:0 14px; background:var(--gold); border:none; border-radius:6px;
                    color:#111; font-size:13px; font-weight:700; cursor:pointer;">
                    📤 Enviar este
                </button>
                <button onclick="fecharPreview()"
                    style="background:none; border:1px solid #444; color:#aaa; border-radius:6px;
                    padding:0 12px; height:32px; font-size:13px; cursor:pointer;">✕ Fechar</button>
            </div>
        </div>
        <iframe id="preview-frame" style="flex:1; border:none; width:100%;"></iframe>
    </div>
</div>

<style>
.ronda-row {
    display:grid;
    grid-template-columns:36px 60px 1fr 120px 110px 100px 130px;
    align-items:center;
    gap:10px;
    padding:11px 20px;
    border-bottom:1px solid rgba(255,255,255,0.05);
    transition:background .12s;
    font-size:13px;
}
.ronda-row:hover { background:rgba(255,255,255,0.03); }
.ronda-row.selected { background:rgba(245,196,0,0.06); }
.ronda-header {
    background:rgba(255,255,255,0.03);
    font-size:11px;
    font-weight:700;
    color:#666;
    text-transform:uppercase;
    letter-spacing:.06em;
    border-bottom:1px solid rgba(255,255,255,0.08);
}
.badge-status {
    display:inline-block; padding:2px 8px; border-radius:20px;
    font-size:11px; font-weight:600; white-space:nowrap;
}
.st-fin  { background:rgba(25,135,84,.15);  color:#28a745; border:1px solid rgba(25,135,84,.3); }
.st-and  { background:rgba(13,110,253,.12); color:#4d9cf5; border:1px solid rgba(13,110,253,.3); }
.st-err  { background:rgba(220,53,69,.12);  color:#dc3545; border:1px solid rgba(220,53,69,.3); }
.btn-row {
    height:26px; padding:0 10px; border-radius:5px; border:1px solid rgba(255,255,255,0.12);
    background:rgba(255,255,255,0.05); color:#ccc; font-size:11px; cursor:pointer;
    display:inline-flex; align-items:center; gap:4px; transition:all .15s; white-space:nowrap;
}
.btn-row:hover { border-color:var(--gold); color:var(--gold); }
.btn-row.enviar:hover { border-color:#28a745; color:#28a745; }
</style>

<script>
let rondasEncontradas = [];
let previewAtualId = null;

document.addEventListener('DOMContentLoaded', () => {
    ajustarPeriodo();
    buscarRondas();
});

function ajustarPeriodo() {
    const v = document.getElementById('f-periodo').value;
    const hoje = new Date(), fmt = d => d.toISOString().slice(0,10);
    const ini = document.getElementById('f-data-ini');
    const fim = document.getElementById('f-data-fim');
    fim.value = fmt(hoje);
    if (v === 'hoje') ini.value = fmt(hoje);
    else if (v === '7d') { const d = new Date(hoje); d.setDate(d.getDate()-6); ini.value = fmt(d); }
    else if (v === '30d') { const d = new Date(hoje); d.setDate(d.getDate()-29); ini.value = fmt(d); }
    ini.disabled = fim.disabled = (v !== 'custom');
}

function limparFiltros() {
    document.getElementById('f-turno').value = '';
    document.getElementById('f-monitor').value = '';
    document.getElementById('f-status').value = '';
    document.getElementById('f-periodo').value = 'hoje';
    ajustarPeriodo();
    buscarRondas();
}

async function buscarRondas() {
    const params = new URLSearchParams({
        data_ini:  document.getElementById('f-data-ini').value,
        data_fim:  document.getElementById('f-data-fim').value,
        turno:     document.getElementById('f-turno').value,
        monitor:   document.getElementById('f-monitor').value,
        status:    document.getElementById('f-status').value,
    });

    const wrap = document.getElementById('tabela-wrap');
    wrap.innerHTML = '<div style="padding:40px; text-align:center; color:#555; font-size:13px;">⏳ Buscando...</div>';

    try {
        const r = await fetch('/api/email/rondas?' + params);
        const d = await r.json();
        rondasEncontradas = d.rondas || [];
        renderTabela(rondasEncontradas);
    } catch(e) {
        wrap.innerHTML = `<div style="padding:40px; text-align:center; color:#dc3545; font-size:13px;">❌ Erro: ${e.message}</div>`;
    }
}

function renderTabela(rondas) {
    const wrap = document.getElementById('tabela-wrap');
    document.getElementById('total-label').textContent = `${rondas.length} registro(s)`;
    document.getElementById('chk-all').checked = false;
    atualizarContador();

    if (!rondas.length) {
        wrap.innerHTML = '<div style="padding:60px 20px; text-align:center; color:#555;"><div style="font-size:36px;margin-bottom:12px;opacity:.4;">🔍</div><p style="font-size:14px;">Nenhum relatório encontrado com os filtros aplicados.</p></div>';
        return;
    }

    const stMap = {
        finalizado:   ['st-fin', '✅ Finalizado'],
        em_andamento: ['st-and', '⏳ Em andamento'],
        erro:         ['st-err', '❌ Com erro'],
    };

    let html = `
    <div class="ronda-row ronda-header">
        <span></span>
        <span>ID</span>
        <span>Monitor / Turno</span>
        <span>Data/Hora</span>
        <span>Status</span>
        <span>Duração</span>
        <span>Ações</span>
    </div>`;

    rondas.forEach(r => {
        const [sc, sl] = stMap[r.status] || ['st-err', r.status];
        const hora = r.iniciada_em ? r.iniciada_em.slice(0,16).replace('T',' ') : '—';
        const dur = calcDuracao(r.iniciada_em, r.finalizada_em);
        html += `
        <div class="ronda-row" id="row-${r.id}" onclick="toggleRow(${r.id})">
            <div onclick="event.stopPropagation()">
                <input type="checkbox" class="row-chk" data-id="${r.id}"
                    style="accent-color:var(--gold); width:14px; height:14px;"
                    onchange="atualizarContador()">
            </div>
            <span style="font-family:monospace; color:#aaa;">#${r.id}</span>
            <div>
                <div style="font-weight:600; color:#e0e0e0;">${r.monitor_nome}</div>
                <div style="font-size:11px; color:#666; margin-top:2px;">🕐 ${r.turno}</div>
            </div>
            <span style="font-size:12px; color:#bbb;">${hora}</span>
            <span><span class="badge-status ${sc}">${sl}</span></span>
            <span style="font-size:12px; color:#888;">${dur}</span>
            <div style="display:flex; gap:5px;" onclick="event.stopPropagation()">
                <button class="btn-row" onclick="verPreview(${r.id}, '${r.monitor_nome} #${r.id}')">👁 Ver</button>
                <button class="btn-row enviar" onclick="enviarUnico(${r.id})">📤 Enviar</button>
            </div>
        </div>`;
    });

    wrap.innerHTML = html;
}

function calcDuracao(ini, fim) {
    if (!ini || !fim) return '—';
    try {
        const diff = Math.floor((new Date(fim) - new Date(ini)) / 1000);
        const h = Math.floor(diff / 3600), m = Math.floor((diff % 3600) / 60);
        return h > 0 ? `${h}h ${m}min` : `${m}min`;
    } catch { return '—'; }
}

function toggleRow(id) {
    const chk = document.querySelector(`.row-chk[data-id="${id}"]`);
    if (chk) { chk.checked = !chk.checked; atualizarContador(); }
    const row = document.getElementById(`row-${id}`);
    if (row) row.classList.toggle('selected', chk.checked);
}

function toggleTodos(el) {
    document.querySelectorAll('.row-chk').forEach(c => {
        c.checked = el.checked;
        const row = document.getElementById(`row-${c.dataset.id}`);
        if (row) row.classList.toggle('selected', el.checked);
    });
    atualizarContador();
}

function atualizarContador() {
    const n = document.querySelectorAll('.row-chk:checked').length;
    document.getElementById('sel-count').textContent =
        n > 0 ? `✅ ${n} relatório(s) selecionado(s)` : '';
}

function getSelecionados() {
    return [...document.querySelectorAll('.row-chk:checked')].map(c => parseInt(c.dataset.id));
}

function getDestinatarios() {
    return document.getElementById('email-destinatarios').value
        .split(/[,\n]/).map(s => s.trim()).filter(Boolean);
}

async function enviarUnico(id) {
    const dests = getDestinatarios();
    if (!dests.length) { toast('Informe ao menos um destinatário.', 'error'); return; }
    await enviarRelatorios([id], dests);
}

async function enviarSelecionados() {
    const ids = getSelecionados();
    if (!ids.length) { toast('Selecione ao menos um relatório.', 'error'); return; }
    const dests = getDestinatarios();
    if (!dests.length) { toast('Informe ao menos um destinatário.', 'error'); return; }
    await enviarRelatorios(ids, dests);
}

async function enviarRelatorios(ids, destinatarios) {
    const el = document.getElementById('resultado-envio');
    el.style.display = 'block';
    el.style.borderColor = '#555';
    el.style.color = '#aaa';
    el.innerHTML = `⏳ Enviando ${ids.length} relatório(s)...`;

    let ok = 0, erros = [];
    for (const id of ids) {
        try {
            const r = await fetch('/api/email/enviar-relatorio', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ronda_id: id, destinatarios}),
            }).then(r => r.json());
            if (r.ok) ok++; else erros.push(`#${id}: ${r.erro}`);
        } catch(e) { erros.push(`#${id}: ${e.message}`); }
    }

    if (!erros.length) {
        el.style.borderColor = '#28a745';
        el.style.color = '#28a745';
        el.innerHTML = `✅ ${ok} relatório(s) enviado(s) com sucesso!`;
        toast(`✅ ${ok} relatório(s) enviado(s)!`, 'ok');
    } else {
        el.style.borderColor = '#dc3545';
        el.style.color = '#dc3545';
        el.innerHTML = `⚠️ ${ok} enviado(s). Erros:<br>${erros.join('<br>')}`;
    }
}

function verPreview(id, titulo) {
    previewAtualId = id;
    document.getElementById('preview-titulo').textContent = `👁 Preview — ${titulo}`;
    document.getElementById('preview-frame').src = `/api/email/preview/${id}`;
    document.getElementById('preview-overlay').style.display = 'flex';
}

function fecharPreview() {
    document.getElementById('preview-overlay').style.display = 'none';
    document.getElementById('preview-frame').src = '';
    previewAtualId = null;
}

async function enviarPreviewAtual() {
    if (!previewAtualId) return;
    const dests = getDestinatarios();
    if (!dests.length) { toast('Informe destinatários no painel de filtros.', 'error'); return; }
    fecharPreview();
    await enviarRelatorios([previewAtualId], dests);
}

function toast(msg, tipo) {
    let ct = document.getElementById('toast-ct');
    if (!ct) {
        ct = document.createElement('div');
        ct.id = 'toast-ct';
        ct.style.cssText = 'position:fixed;bottom:24px;right:24px;display:flex;flex-direction:column;gap:8px;z-index:9000;';
        document.body.appendChild(ct);
    }
    const el = document.createElement('div');
    el.style.cssText = `font-size:13px;padding:12px 18px;border-radius:8px;background:#1e1e1e;
        box-shadow:0 8px 32px rgba(0,0,0,.5);
        border-left:4px solid ${tipo==='ok'?'#28a745':'#dc3545'};
        color:${tipo==='ok'?'#4ade80':'#f87171'};max-width:340px;`;
    el.textContent = msg;
    ct.appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharPreview(); });
</script>
{% endblock %}

{% extends "base.html" %}
{% block title %}Histórico — Ronda Automatizada{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Histórico de Rondas</h1>
</div>

<div class="card">
    <div class="card-title">Todas as Rondas</div>

    {% if rondas %}
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Monitor</th>
                <th>Turno</th>
                <th>Iniciada em</th>
                <th>Finalizada em</th>
                <th>Status</th>
                <th>Relatório</th>
            </tr>
        </thead>
        <tbody>
            {% for r in rondas %}
            <tr>
                <td style="color: #666; font-size: 12px;">{{ r.id }}</td>
                <td style="font-weight: 600;">{{ r.monitor_nome }}</td>
                <td>{{ r.turno }}</td>
                <td>{{ r.iniciada_em }}</td>
                <td>{{ r.finalizada_em or '—' }}</td>
                <td>
                    {% if r.status == 'finalizada' %}
                        <span class="badge badge-success">Finalizada</span>
                    {% elif r.status == 'com_alertas' %}
                        <span class="badge badge-danger">⚠️ Com Alertas</span>
                    {% elif r.status == 'em_andamento' %}
                        <span class="badge badge-warning">Em andamento</span>
                    {% else %}
                        <span class="badge badge-danger">Erro</span>
                    {% endif %}
                </td>
                <td>
                    {% if r.status != 'em_andamento' %}
                    <a href="{{ url_for('rondas.ver_relatorio_multi', ronda_id=r.id) }}"
                       class="btn btn-primary btn-sm">Ver</a>
                    {% else %}
                    <span style="font-size: 12px; color: #666;">Aguardando...</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p style="color: #888; font-size: 14px; text-align: center; padding: 2rem 0;">
        Nenhuma ronda registrada ainda.
    </p>
    {% endif %}
</div>
{% endblock %}

<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Login — Grupo Ronda</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --gold: #f5c400;
            --gold-dim: #c49a00;
        }

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'DM Sans', sans-serif;
            background: #080809;
            color: #fff;
            min-height: 100vh;
            display: flex;
            overflow: hidden;
        }

        /* ── LEFT PANEL ── */
        .left {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 3rem;
            position: relative;
            background:
                radial-gradient(ellipse 80% 60% at 20% 110%, rgba(245,196,0,0.12), transparent),
                radial-gradient(ellipse 40% 40% at 80% -10%, rgba(245,196,0,0.06), transparent),
                #0a0a0b;
            border-right: 1px solid rgba(255,255,255,0.05);
        }

        /* Dot grid texture */
        .left::before {
            content: '';
            position: absolute;
            inset: 0;
            background-image: radial-gradient(circle, rgba(245,196,0,0.08) 1px, transparent 1px);
            background-size: 28px 28px;
            pointer-events: none;
        }

        .left-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            position: relative;
        }
        .left-brand img {
            width: 44px; height: 44px;
            object-fit: contain;
            border-radius: 8px;
            border: 1px solid rgba(245,196,0,0.3);
        }
        .left-brand-name {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .left-brand-name span { color: var(--gold); }

        .left-hero {
            position: relative;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .left-hero h2 {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: clamp(42px, 5vw, 64px);
            font-weight: 900;
            line-height: 0.95;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            color: #fff;
            margin-bottom: 1.5rem;
        }
        .left-hero h2 em {
            font-style: normal;
            color: var(--gold);
            display: block;
        }
        .left-hero p {
            font-size: 14px;
            color: rgba(255,255,255,0.4);
            max-width: 380px;
            line-height: 1.7;
            text-align: center;
        }

        .left-stats {
            display: flex;
            gap: 2rem;
            position: relative;
        }
        .stat-item {
            border-left: 2px solid rgba(245,196,0,0.3);
            padding-left: 14px;
        }
        .stat-item-value {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 20px;
            font-weight: 800;
            color: var(--gold);
            line-height: 1.1;
        }
        .stat-item-label {
            font-size: 10px;
            color: rgba(255,255,255,0.3);
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-top: 3px;
        }

        /* ── RIGHT PANEL ── */
        .right {
            width: 420px;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 3rem;
            background: #0d0d0f;
        }

        .login-title {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 28px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #fff;
            margin-bottom: 6px;
        }
        .login-subtitle {
            font-size: 13px;
            color: rgba(255,255,255,0.3);
            margin-bottom: 2.5rem;
        }

        .form-group { margin-bottom: 1.1rem; }
        label {
            display: block;
            font-size: 11px;
            font-weight: 700;
            color: rgba(255,255,255,0.3);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 7px;
        }
        input {
            width: 100%;
            padding: 12px 14px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            color: #fff;
            font-size: 14px;
            font-family: 'DM Sans', sans-serif;
            transition: all 0.2s;
        }
        input::placeholder { color: rgba(255,255,255,0.2); }
        input:focus {
            outline: none;
            border-color: rgba(245,196,0,0.5);
            background: rgba(245,196,0,0.04);
            box-shadow: 0 0 0 3px rgba(245,196,0,0.08);
        }

        .btn-login {
            width: 100%;
            padding: 13px;
            margin-top: 6px;
            background: var(--gold);
            color: #111;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            font-family: 'Barlow Condensed', sans-serif;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-login:hover {
            background: #ffd633;
            transform: translateY(-2px);
            box-shadow: 0 8px 28px rgba(245,196,0,0.25);
        }
        .btn-login:active { transform: scale(0.98); }

        .alert {
            padding: 11px 14px;
            border-radius: 9px;
            margin-bottom: 1.2rem;
            font-size: 13px;
            font-weight: 500;
            border: 1px solid transparent;
        }
        .alert-danger  { background: rgba(232,64,87,0.1);   border-color: rgba(232,64,87,0.3);   color: #f87171; }
        .alert-warning { background: rgba(249,115,22,0.1);  border-color: rgba(249,115,22,0.3);  color: #fb923c; }
        .alert-success { background: rgba(34,197,94,0.1);   border-color: rgba(34,197,94,0.3);   color: #4ade80; }
        .alert-info    { background: rgba(59,130,246,0.1);  border-color: rgba(59,130,246,0.3);  color: #60a5fa; }

        .login-footer {
            margin-top: 2.5rem;
            font-size: 11px;
            color: rgba(255,255,255,0.15);
            text-align: center;
        }

        /* ── RESPONSIVE ── */
        @media (max-width: 768px) {
            body { flex-direction: column; }
            .left { display: none; }
            .right {
                width: 100%;
                min-height: 100vh;
                padding: 2rem 1.5rem;
                justify-content: center;
            }
        }

        /* ── ANIMATE IN ── */
        .right > * {
            animation: fadeUp 0.4s ease both;
        }
        .right > *:nth-child(1) { animation-delay: 0.05s; }
        .right > *:nth-child(2) { animation-delay: 0.1s; }
        .right > *:nth-child(3) { animation-delay: 0.15s; }
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(12px); }
            to   { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>

<!-- LEFT: brand panel -->
<div class="left">
    <div class="left-brand">
        <img src="{{ url_for('static', filename='img/logo.jpeg') }}" alt="Grupo Ronda">
        <span class="left-brand-name">GRUPO <span>RONDA</span></span>
    </div>

    <div class="left-hero">
        <h2>
            Monitoramento
            <em>Inteligente</em>
            24 Horas
        </h2>
        <p>
            Vigilância patrimonial de alta performance com cobertura
            total do perímetro. Registros auditáveis, alertas imediatos
            e relatórios detalhados por turno operacional.
        </p>
    </div>

    <div class="left-stats">
        <div class="stat-item">
            <div class="stat-item-value">24/7</div>
            <div class="stat-item-label">Operação contínua</div>
        </div>
        <div class="stat-item">
            <div class="stat-item-value">100%</div>
            <div class="stat-item-label">Rastreabilidade</div>
        </div>
        <div class="stat-item">
            <div class="stat-item-value">TEMPO REAL</div>
            <div class="stat-item-label">Alertas imediatos</div>
        </div>
        <div class="stat-item">
            <div class="stat-item-value">MULTI-SITE</div>
            <div class="stat-item-label">Gestão centralizada</div>
        </div>
    </div>
</div>

<!-- RIGHT: login form -->
<div class="right">
    <div class="login-title">Entrar</div>
    <div class="login-subtitle">Acesse com suas credenciais de monitor</div>

    {% for category, message in get_flashed_messages(with_categories=true) %}
    <div class="alert alert-{{ category }}">{{ message }}</div>
    {% endfor %}

    <form method="POST">
        <div class="form-group">
            <label for="usuario">Usuário</label>
            <input type="text" id="usuario" name="usuario"
                   placeholder="seu.usuario" autofocus required>
        </div>
        <div class="form-group">
            <label for="senha">Senha</label>
            <input type="password" id="senha" name="senha"
                   placeholder="••••••••" required>
        </div>
        <button type="submit" class="btn-login">Entrar no Sistema</button>
    </form>

    <div class="login-footer">Grupo Ronda © 2026 — Sistema de Segurança Patrimonial</div>
</div>

</body>
</html>


{% extends "base.html" %}
{% block title %}Monitor WhatsApp — Grupo Ronda{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Monitor WhatsApp</h1>
    <button onclick="location.reload()" class="btn btn-primary">↻ Atualizar</button>
</div>

<!-- STATUS DO SISTEMA -->
<div class="card" style="background: #0a0a0a; border-color: #f5c400;">
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 14px; height: 14px; border-radius: 50%;
                background: {{ '#22c55e' if sistema_online else '#ef4444' }};
                box-shadow: 0 0 8px {{ '#22c55e' if sistema_online else '#ef4444' }};">
            </div>
            <div>
                <div style="font-size: 15px; font-weight: 700; color: #fff;">
                    WhatsApp {{ 'ONLINE' if sistema_online else 'DESCONECTADO' }}
                </div>
                <div style="font-size: 12px; color: #aaa;">
                    {% if sistema_atraso is not none %}
                        Último heartbeat há {{ sistema_atraso }}s
                    {% else %}
                        Nenhum heartbeat recebido ainda
                    {% endif %}
                </div>
            </div>
        </div>
        <div style="font-size: 12px; color: #aaa;">
            Atualizado em: <span id="hora-atual" style="color: #f5c400;"></span>
        </div>
    </div>
</div>

<!-- CARDS DE RESUMO -->
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
    <div class="card" style="text-align: center; border-top: 3px solid #22c55e; margin-bottom: 0;">
        <div style="font-size: 36px; font-weight: 700; color: #22c55e;">{{ total_ok }}</div>
        <div style="font-size: 13px; color: #888; margin-top: 4px;">🟢 OK</div>
    </div>
    <div class="card" style="text-align: center; border-top: 3px solid #f59e0b; margin-bottom: 0;">
        <div style="font-size: 36px; font-weight: 700; color: #f59e0b;">{{ total_alerta }}</div>
        <div style="font-size: 13px; color: #888; margin-top: 4px;">🟡 Alerta</div>
    </div>
    <div class="card" style="text-align: center; border-top: 3px solid #ef4444; margin-bottom: 0;">
        <div style="font-size: 36px; font-weight: 700; color: #ef4444;">{{ total_critico }}</div>
        <div style="font-size: 13px; color: #888; margin-top: 4px;">🔴 Crítico</div>
    </div>
</div>

<!-- STATUS POR GRUPO -->
<div class="card">
    <div class="card-title">Status por Grupo</div>
    {% if grupos %}
    <table>
        <thead>
            <tr>
                <th>Grupo</th>
                <th>Última Mensagem</th>
                <th>Inativo</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for g in grupos %}
            <tr>
                <td style="font-weight: 600;">{{ g.nome }}</td>
                <td>{{ g.ultima_msg }}</td>
                <td>{{ g.inativo_min }} min</td>
                <td>
                    {% if g.status == 'OK' %}
                        <span class="badge" style="background: #d4edda; color: #6ee7a0;">🟢 OK</span>
                    {% elif g.status == 'ALERTA' %}
                        <span class="badge" style="background: #fff3cd; color: #856404;">🟡 Alerta</span>
                    {% else %}
                        <span class="badge" style="background: #f8d7da; color: #f88;">🔴 Crítico</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p style="color: #888; font-size: 14px; text-align: center; padding: 2rem 0;">
        Nenhum grupo UFV Segurança encontrado nas últimas 24h.<br>
        Verifique se o <strong>server.js</strong> está em execução e conectado ao WhatsApp.
    </p>
    {% endif %}
</div>

<!-- HISTÓRICO DE MENSAGENS -->
<div class="card">
    <div class="card-title">Histórico de Mensagens (últimas 50)</div>
    {% if historico %}
    <table>
        <thead>
            <tr>
                <th>Horário</th>
                <th>Grupo</th>
                <th>Autor</th>
                <th>Mensagem</th>
            </tr>
        </thead>
        <tbody>
            {% for h in historico %}
            <tr>
                <td style="font-size: 12px; color: #666; white-space: nowrap;">
                    {{ h.data[:19].replace('T', ' ') if h.data else '—' }}
                </td>
                <td style="font-size: 13px; font-weight: 600;">{{ h.grupo }}</td>
                <td style="font-size: 13px;">{{ h.autor or '—' }}</td>
                <td style="font-size: 13px; color: #aaa;">{{ h.conteudo or '—' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p style="color: #888; font-size: 14px; text-align: center; padding: 2rem 0;">
        Nenhuma mensagem registrada ainda.
    </p>
    {% endif %}
</div>

<script>
    function atualizarHora() {
        const el = document.getElementById('hora-atual');
        if (el) el.textContent = new Date().toLocaleString('pt-BR');
    }
    atualizarHora();
    setInterval(atualizarHora, 1000);

    // Auto-refresh a cada 60 segundos
    setTimeout(() => location.reload(), 60000);
</script>
{% endblock %}

{% extends "base.html" %}
{% block title %}Monitores — Ronda Automatizada{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Monitores</h1>
    <a href="{{ url_for('rondas.novo_monitor') }}" class="btn btn-primary">+ Novo Monitor</a>
</div>

<div class="card">
    <div class="card-title">Monitores Cadastrados</div>

    {% if monitores %}
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Nome</th>
                <th>Usuário</th>
                <th>Turno</th>
            </tr>
        </thead>
        <tbody>
            {% for m in monitores %}
            <tr>
                <td style="color: #666; font-size: 12px;">{{ m.id }}</td>
                <td style="font-weight: 600;">{{ m.nome }}</td>
                <td style="font-family: monospace; font-size: 13px;">{{ m.usuario }}</td>
                <td><span class="badge badge-info">{{ m.turno }}</span></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p style="color: #888; font-size: 14px; text-align: center; padding: 2rem 0;">
        Nenhum monitor cadastrado.
    </p>
    {% endif %}
</div>
{% endblock %}

{% extends "base.html" %}
{% block title %}Novo Monitor — Ronda Automatizada{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Novo Monitor</h1>
    <a href="{{ url_for('rondas.monitores') }}" class="btn btn-primary btn-sm">← Voltar</a>
</div>

<div class="card" style="max-width: 480px;">
    <div class="card-title">Cadastrar Monitor</div>

    <form method="POST">
        <div class="form-group">
            <label for="nome">Nome completo</label>
            <input type="text" id="nome" name="nome" placeholder="Ex: João Silva" required>
        </div>
        <div class="form-group">
            <label for="usuario">Usuário (login)</label>
            <input type="text" id="usuario" name="usuario" placeholder="Ex: joao.silva" required>
        </div>
        <div class="form-group">
            <label for="senha">Senha</label>
            <input type="password" id="senha" name="senha" placeholder="Mínimo 6 caracteres" required>
        </div>
        <div class="form-group">
            <label for="turno">Turno</label>
            <select id="turno" name="turno" required>
                <option value="">Selecione o turno</option>
                <option value="Turno A (06h–14h)">Turno A (06h–14h)</option>
                <option value="Turno B (14h–22h)">Turno B (14h–22h)</option>
                <option value="Turno C (22h–06h)">Turno C (22h–06h)</option>
                <option value="Administrativo">Administrativo</option>
            </select>
        </div>
        <button type="submit" class="btn btn-success">Cadastrar Monitor</button>
    </form>
</div>
{% endblock %}

{% extends "base.html" %}
{% block title %}Relatório #{{ ronda.id }} — Grupo Ronda{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Relatório de Ronda #{{ ronda.id }}</h1>
    <a href="{{ url_for('rondas.historico') }}" class="btn btn-primary btn-sm">← Voltar</a>
</div>

<!-- INFORMAÇÕES DA RONDA -->
<div class="card">
    <div class="card-title">Informações da Ronda</div>
    <table style="width: auto;">
        <tr>
            <td style="font-weight:600; padding-right:2rem; color:#888; font-size:13px;">Monitor</td>
            <td style="font-weight:700; font-size:15px;">{{ ronda.monitor_nome }}</td>
        </tr>
        <tr>
            <td style="font-weight:600; color:#888; font-size:13px;">Turno</td>
            <td>{{ ronda.turno }}</td>
        </tr>
        <tr>
            <td style="font-weight:600; color:#888; font-size:13px;">Iniciada em</td>
            <td>{{ ronda.iniciada_em }}</td>
        </tr>
        <tr>
            <td style="font-weight:600; color:#888; font-size:13px;">Finalizada em</td>
            <td>{{ ronda.finalizada_em or '—' }}</td>
        </tr>
        <tr>
            <td style="font-weight:600; color:#888; font-size:13px;">Status</td>
            <td>
                {% if ronda.status == 'finalizada' %}
                    <span class="badge badge-success">Finalizada</span>
                {% elif ronda.status == 'com_alertas' %}
                    <span class="badge badge-danger">⚠️ Com Alertas</span>
                {% elif ronda.status == 'em_andamento' %}
                    <span class="badge badge-warning">Em andamento</span>
                {% else %}
                    <span class="badge badge-danger">Erro</span>
                {% endif %}
            </td>
        </tr>
    </table>
</div>

{% if dados %}

    <!-- ── RONDA MULTI-NVR ── -->
    {% if dados.nvrs is defined %}

        {% set total_invasoes = namespace(v=0) %}
        {% for nvr in dados.nvrs %}{% set total_invasoes.v = total_invasoes.v + nvr.invasoes %}{% endfor %}

        {% if total_invasoes.v > 0 %}
        <div style="background:rgba(220,53,69,0.15); border:1px solid rgba(220,53,69,0.3); border-radius:8px;
                    padding:10px 16px; margin-bottom:1rem; color:#f88; font-size:14px;">
            ⚠️ <strong>{{ total_invasoes.v }} detecção(ões) em {{ dados.nvrs|length }} NVR(s)</strong>
        </div>
        {% else %}
        <div style="background:rgba(25,135,84,0.15); border:1px solid rgba(25,135,84,0.3); border-radius:8px;
                    padding:10px 16px; margin-bottom:1rem; color:#6ee7a0; font-size:14px;">
            ✅ <strong>Ronda concluída sem detecções em todos os NVRs</strong>
        </div>
        {% endif %}

        {% for nvr in dados.nvrs %}
        <div class="card" style="margin-bottom:1.5rem;">

            <div style="display:flex; justify-content:space-between; align-items:center;
                        margin-bottom:1rem; padding-bottom:0.75rem; border-bottom:2px solid #f5c400;">
                <div>
                    <span style="font-size:16px; font-weight:700; color:#fff;">📷 {{ nvr.nome }}</span>
                    <span style="font-size:12px; color:#888; margin-left:10px;">{{ nvr.ip }}</span>
                </div>
                <div>
                    {% if nvr.erro %}
                        <span class="badge badge-danger">❌ Erro</span>
                    {% elif nvr.invasoes > 0 %}
                        <span class="badge badge-danger">⚠️ {{ nvr.invasoes }} invasão(ões)</span>
                    {% else %}
                        <span class="badge badge-success">✅ Normal</span>
                    {% endif %}
                </div>
            </div>

            {% if nvr.erro %}
                <p style="color:#dc3545; font-size:14px;">Falha: {{ nvr.erro }}</p>
            {% elif nvr.linhas %}
                <table>
                    <thead>
                        <tr>
                            <th>Horário</th>
                            <th>Local</th>
                            <th>Status</th>
                            <th>Pessoas</th>
                            <th>Imagem</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for linha in nvr.linhas %}
                        <tr>
                            <td style="font-size:13px; color:#888; white-space:nowrap;">{{ linha.horario }}</td>
                            <td style="font-weight:600;">{{ linha.nome_local }}</td>
                            <td>
                                {% if linha.pessoas > 0 %}
                                    <span class="badge badge-danger">⚠️ INVASÃO</span>
                                {% else %}
                                    <span class="badge badge-success">✅ NORMAL</span>
                                {% endif %}
                            </td>
                            <td style="text-align:center;">
                                {% if linha.pessoas > 0 %}
                                    <strong style="color:#dc3545;">{{ linha.pessoas }}</strong>
                                {% else %}
                                    <span style="color:#888;">0</span>
                                {% endif %}
                            </td>
                            <td>
                                <img src="/relatorios/{{ pasta_name }}/{{ nvr.id }}/imagens/{{ linha.nome_local }}.jpg"
                                     style="width:300px; border-radius:6px; border:1px solid #2a2a2a;"
                                     onerror="this.style.display='none'">
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                <div style="padding:10px 0 0; font-size:13px; color:#888;
                            border-top:1px solid #1e1e1e; margin-top:0.5rem;">
                    Presets: <strong>{{ nvr.linhas|length }}</strong> &nbsp;|&nbsp;
                    Invasões: <strong {% if nvr.invasoes > 0 %}style="color:#dc3545"{% endif %}>{{ nvr.invasoes }}</strong> &nbsp;|&nbsp;
                    Duração: <strong>{{ nvr.duracao_s }}s</strong>
                </div>
            {% else %}
                <p style="color:#888; font-size:14px;">Nenhum dado para este NVR.</p>
            {% endif %}

        </div>
        {% endfor %}

    <!-- ── RONDA SIMPLES (1 NVR) ── -->
    {% else %}

        {% set total_invasoes = namespace(v=0) %}
        {% for l in dados.linhas %}{% if l.pessoas > 0 %}{% set total_invasoes.v = total_invasoes.v + l.pessoas %}{% endif %}{% endfor %}

        {% if total_invasoes.v > 0 %}
        <div style="background:rgba(220,53,69,0.15); border:1px solid rgba(220,53,69,0.3); border-radius:8px;
                    padding:10px 16px; margin-bottom:1rem; color:#f88; font-size:14px;">
            ⚠️ <strong>{{ total_invasoes.v }} pessoa(s) detectada(s)</strong>
        </div>
        {% else %}
        <div style="background:rgba(25,135,84,0.15); border:1px solid rgba(25,135,84,0.3); border-radius:8px;
                    padding:10px 16px; margin-bottom:1rem; color:#6ee7a0; font-size:14px;">
            ✅ <strong>Ronda concluída sem detecções</strong>
        </div>
        {% endif %}

        <div class="card">
            <div class="card-title">Resultado da Ronda</div>
            <table>
                <thead>
                    <tr>
                        <th>Horário</th>
                        <th>Local</th>
                        <th>Status</th>
                        <th>Pessoas</th>
                        <th>Imagem</th>
                    </tr>
                </thead>
                <tbody>
                    {% for linha in dados.linhas %}
                    <tr>
                        <td style="font-size:13px; color:#888; white-space:nowrap;">{{ linha.horario }}</td>
                        <td style="font-weight:600;">{{ linha.nome_local }}</td>
                        <td>
                            {% if linha.pessoas > 0 %}
                                <span class="badge badge-danger">⚠️ INVASÃO</span>
                            {% else %}
                                <span class="badge badge-success">✅ NORMAL</span>
                            {% endif %}
                        </td>
                        <td style="text-align:center;">
                            {% if linha.pessoas > 0 %}
                                <strong style="color:#dc3545;">{{ linha.pessoas }}</strong>
                            {% else %}
                                <span style="color:#888;">0</span>
                            {% endif %}
                        </td>
                        <td>
                            <img src="{{ img_prefix }}{{ linha.nome_local }}.jpg"
                                 style="width:300px; border-radius:6px; border:1px solid #2a2a2a;"
                                 onerror="this.style.display='none'">
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

    {% endif %}

{% else %}
<div class="card">
    <p style="color:#888; font-size:14px; text-align:center; padding:2rem 0;">
        Relatório ainda não disponível. A ronda pode estar em andamento.
    </p>
</div>
{% endif %}

{% endblock %}

{% extends "base.html" %}
{% block title %}Ronda Contínua — Grupo Ronda{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Ronda Contínua</h1>
    <span id="badge-status" class="badge badge-secondary" style="font-size:13px; padding:6px 14px;">⏹ Inativo</span>
</div>

<!-- CARDS DE STATUS -->
<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin-bottom:1.5rem;">
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #6c757d;">
        <div style="font-size:28px; font-weight:700; color:#333;" id="card-ciclo">—</div>
        <div style="font-size:12px; color:#888; margin-top:4px;">🔄 Ciclo Atual</div>
    </div>
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #198754;">
        <div style="font-size:28px; font-weight:700; color:#198754;" id="card-total">0</div>
        <div style="font-size:12px; color:#888; margin-top:4px;">✅ Ciclos Concluídos</div>
    </div>
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #f5c400;">
        <div style="font-size:13px; font-weight:600; color:#333; margin-top:4px;" id="card-inicio">—</div>
        <div style="font-size:12px; color:#888; margin-top:4px;">🕐 Iniciado em</div>
    </div>
    <div class="card" style="text-align:center; margin-bottom:0; border-top:3px solid #0dcaf0;">
        <div style="font-size:13px; font-weight:600; color:#333; margin-top:4px;" id="card-ultimo">—</div>
        <div style="font-size:12px; color:#888; margin-top:4px;">⏱ Último Ciclo</div>
    </div>
</div>

<div style="display:grid; grid-template-columns:1fr 1fr; gap:1.5rem;">

    <!-- PAINEL DE CONTROLE -->
    <div class="card">
        <div class="card-title">️ Controle do Loop</div>

        <div class="form-group">
            <label>Monitor</label>
            <input type="text" id="inp-monitor" value="{{ monitor_nome }}" placeholder="Nome do monitor">
        </div>
        <div class="form-group">
            <label>Turno</label>
            <select id="inp-turno">
                <option value="Diurno"  {% if turno == 'Diurno'  %}selected{% endif %}>Diurno</option>
                <option value="Noturno" {% if turno == 'Noturno' %}selected{% endif %}>Noturno</option>
            </select>
        </div>

        <div class="form-group">
            <label>NVRs a monitorar</label>
            <div style="display:flex; flex-direction:column; gap:6px; margin-top:4px;">
                <label style="font-weight:400; color:#aaa; display:flex; gap:8px; align-items:center; cursor:pointer;">
                    <input type="checkbox" id="chk-todos-nvrs" checked onchange="toggleTodosNvrs(this)">
                    <span style="font-weight:600;">Todos os NVRs</span>
                </label>
                <div id="lista-nvrs" style="display:none; padding-left:20px; display:flex; flex-direction:column; gap:4px;">
                    {% for nvr in nvrs %}
                    <label style="font-weight:400; color:#aaa; display:flex; gap:8px; align-items:center; cursor:pointer;">
                        <input type="checkbox" class="chk-nvr" value="{{ nvr.id }}" checked>
                        {{ nvr.site }} - {{ nvr.nome }} ({{ nvr.ip }})
                    </label>
                    {% endfor %}
                </div>
            </div>
        </div>

        <div style="display:flex; gap:10px; margin-top:1rem;">
            <button id="btn-iniciar" onclick="iniciarLoop()" class="btn btn-success" style="flex:1;">
                ▶ Iniciar Loop
            </button>
            <button id="btn-parar" onclick="pararLoop()" class="btn btn-danger" style="flex:1; display:none;">
                ⏹ Parar após este ciclo
            </button>
        </div>

        <div id="aviso-parada" style="display:none; margin-top:12px; padding:10px 14px;
             background:#fff3cd; border:1px solid #ffeeba; border-radius:6px;
             font-size:13px; color:#856404;">
            ⚠️ Parada solicitada. O loop encerrará após o ciclo atual ser concluído.
        </div>

        <div id="aviso-erro" style="display:none; margin-top:12px; padding:10px 14px;
             background:rgba(220,53,69,0.15); border:1px solid rgba(220,53,69,0.3); border-radius:6px;
             font-size:13px; color:#f88;">
        </div>
    </div>

    <!-- LOG EM TEMPO REAL -->
    <div class="card" style="display:flex; flex-direction:column;">
        <div class="card-title" style="display:flex; justify-content:space-between; align-items:center;"><span>📋 Log em Tempo Real</span>
            <button onclick="limparLog()" class="btn btn-primary btn-sm">Limpar</button>
        </div>
        <div id="log-box" style="
            flex:1; min-height:300px; max-height:400px;
            overflow-y:auto; background:#0d1117; border-radius:8px;
            padding:12px; font-family:'Courier New', monospace; font-size:12px;
            color:#7ee787; line-height:1.7;
        ">
            <span style="color:#888;">Aguardando início do loop...</span>
        </div>
    </div>
</div>

<!-- INSTRUÇÃO -->
<div class="card" style="margin-top:0; background:rgba(245,196,0,0.05); border-color:#f5c400;">
    <div style="font-size:13px; color:#888; line-height:1.8;">
        <strong style="color:#fff;">ℹ️ Como funciona:</strong>
        O loop executa rondas automaticamente em sequência — assim que uma termina e gera o relatório, a próxima começa imediatamente.
        Ao clicar em <strong>"Parar após este ciclo"</strong>, a ronda em andamento é concluída normalmente e nenhuma nova é iniciada.
        Todos os alarmes detectados ficam disponíveis na <a href="{{ url_for('alarmes.central_alarmes') }}" style="color:#f5c400;">Central de Alarmes</a>.
    </div>
</div>

<script>
let _polling = null;
let _logUltimoIdx = 0;

// ── Inicializa ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    atualizarStatus();
    _polling = setInterval(atualizarStatus, 3000);
});

// ── Toggle NVRs ─────────────────────────────────────────
function toggleTodosNvrs(chk) {
    const lista = document.getElementById('lista-nvrs');
    lista.style.display = chk.checked ? 'none' : 'flex';
    document.querySelectorAll('.chk-nvr').forEach(c => c.checked = true);
}

// ── Iniciar ─────────────────────────────────────────────
async function iniciarLoop() {
    const monitor = document.getElementById('inp-monitor').value.trim() || 'Não informado';
    const turno   = document.getElementById('inp-turno').value;
    const todos   = document.getElementById('chk-todos-nvrs').checked;
    const nvr_ids = todos
        ? null
        : [...document.querySelectorAll('.chk-nvr:checked')].map(c => c.value);

    if (!todos && nvr_ids.length === 0) {
        toast('Selecione ao menos um NVR.', 'error'); return;
    }

    try {
        const r = await fetch('/api/ronda-loop/iniciar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ monitor_nome: monitor, turno, nvr_ids }),
        }).then(r => r.json());

        if (r.ok) {
            _logUltimoIdx = 0;
            toast('Loop iniciado!', 'ok');
        } else {
            toast(r.erro || 'Erro ao iniciar.', 'error');
        }
    } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

// ── Parar ────────────────────────────────────────────────
async function pararLoop() {
    if (!confirm('Parar o loop após o ciclo atual?')) return;
    try {
        const r = await fetch('/api/ronda-loop/parar', { method: 'POST' }).then(r => r.json());
        if (r.ok) toast('Parada solicitada. Aguardando fim do ciclo...', 'ok');
        else toast(r.erro || 'Erro ao parar.', 'error');
    } catch(e) { toast('Erro: ' + e.message, 'error'); }
}

// ── Polling de status ────────────────────────────────────
async function atualizarStatus() {
    try {
        const s = await fetch('/api/ronda-loop/status').then(r => r.json());
        renderStatus(s);
        renderLog(s.log);
    } catch(_) {}
}

function renderStatus(s) {
    const badge     = document.getElementById('badge-status');
    const btnIni    = document.getElementById('btn-iniciar');
    const btnPar    = document.getElementById('btn-parar');
    const avisoStop = document.getElementById('aviso-parada');
    const avisoErr  = document.getElementById('aviso-erro');

    // Badge e botões
    if (s.ativo && s.parar) {
        badge.className = 'badge badge-warning';
        badge.textContent = '⚠️ Parando...';
        btnIni.style.display = 'none';
        btnPar.style.display = 'none';
        avisoStop.style.display = 'block';
    } else if (s.ativo) {
        badge.className = 'badge badge-success';
        badge.textContent = `▶ Rodando — Ciclo #${s.ciclo_atual}`;
        btnIni.style.display = 'none';
        btnPar.style.display = 'inline-block';
        avisoStop.style.display = 'none';
    } else {
        badge.className = 'badge badge-secondary';
        badge.textContent = '⏹ Inativo';
        btnIni.style.display = 'inline-block';
        btnPar.style.display = 'none';
        avisoStop.style.display = 'none';
    }

    // Erro
    if (s.erro) {
        avisoErr.style.display = 'block';
        avisoErr.textContent = '❌ Último erro: ' + s.erro;
    } else {
        avisoErr.style.display = 'none';
    }

    // Cards
    document.getElementById('card-ciclo').textContent  = s.ativo ? s.ciclo_atual : '—';
    document.getElementById('card-total').textContent  = s.total_ciclos;
    document.getElementById('card-inicio').textContent = s.iniciado_em
        ? s.iniciado_em.slice(0, 16).replace('T', ' ')
        : '—';
    document.getElementById('card-ultimo').textContent = s.ultimo_ciclo
        ? s.ultimo_ciclo.slice(0, 16).replace('T', ' ')
        : '—';
}

function renderLog(linhas) {
    if (!linhas || linhas.length === 0) return;
    const box = document.getElementById('log-box');

    // Limpa placeholder na primeira vez
    if (box.children.length === 1 && box.children[0].tagName === 'SPAN') {
        box.innerHTML = '';
    }

    // Só adiciona linhas novas
    const novas = linhas.slice(_logUltimoIdx);
    if (novas.length === 0) return;

    novas.forEach(linha => {
        const div = document.createElement('div');
        div.textContent = linha;
        if (linha.includes('[WARN]'))      div.style.color = '#f0883e';
        else if (linha.includes('ENCERR')) div.style.color = '#f85149';
        else if (linha.includes('Ciclo #') && linha.includes('concluído')) div.style.color = '#3fb950';
        box.appendChild(div);
    });

    _logUltimoIdx = linhas.length;
    box.scrollTop = box.scrollHeight;
}

function limparLog() {
    document.getElementById('log-box').innerHTML =
        '<span style="color:#888;">Log limpo.</span>';
    _logUltimoIdx = 0;
}

// ── Toast ────────────────────────────────────────────────
function toast(msg, tipo) {
    let ct = document.getElementById('toast-ct');
    if (!ct) {
        ct = document.createElement('div');
        ct.id = 'toast-ct';
        ct.style.cssText = 'position:fixed;bottom:24px;right:24px;display:flex;flex-direction:column;gap:8px;z-index:9000;';
        document.body.appendChild(ct);
    }
    const el = document.createElement('div');
    el.style.cssText = `font-size:13px;padding:12px 18px;border-radius:8px;background:#0f0f0f;
        box-shadow:0 8px 32px rgba(0,0,0,.2);
        border-left:4px solid ${tipo==='ok'?'#28a745':'#dc3545'};
        color:#333;max-width:340px;`;
    el.textContent = msg;
    ct.appendChild(el);
    setTimeout(() => el.remove(), 3500);
}
</script>
{% endblock %}

// Quando a tela é servida pelo próprio Hub, a API é o mesmo endereço.
// No GitHub Pages (outro domínio) o endereço do Hub é informado e lembrado no navegador.
const noPages = location.hostname.endsWith("github.io");
// Hub de testes publicado pelo Tailscale Funnel; pode ser trocado no campo "Servidor da API".
const HUB_PADRAO = "https://office-mscx.tailbf5033.ts.net";
const $ = (id) => document.getElementById(id);
const guardar = (chave, valor) => { try { localStorage.setItem(chave, valor); } catch {} };
const lembrar = (chave) => { try { return localStorage.getItem(chave) || ""; } catch { return ""; } };
const baseApi = () => (noPages ? $("api").value.trim().replace(/\/$/, "") : "");

// Cria elementos sem interpretar HTML: o texto vindo do motor nunca vira marcação.
function el(tag, props = {}, ...filhos) {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...filhos);
  return e;
}

const dinheiro = (v) => Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const hojeLocal = () => new Date().toLocaleDateString("sv-SE");

function mensagemDeErro(corpo) {
  if (corpo && corpo.erro) return corpo.erro;
  if (corpo && Array.isArray(corpo.detail)) return corpo.detail.map((d) => `${d.loc.slice(1).join(".")}: ${d.msg}`).join("\n");
  return "Não foi possível calcular.";
}

// Envia o pedido ao Hub e devolve o corpo; erros viram exceções com mensagem legível.
async function enviarAoHub(caminho, pedido) {
  const resposta = await fetch(`${baseApi()}${caminho}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pedido),
  });
  const corpo = await resposta.json().catch(() => null);
  if (!resposta.ok) throw new Error(mensagemDeErro(corpo));
  return corpo;
}

const MENSAGEM_SEM_HUB = "Não consegui falar com o servidor do Hub. Confira o endereço e se ele está no ar.";

// Mostra o campo do endereço do Hub quando a tela está no GitHub Pages.
function prepararServidor(aoMudar) {
  if (!noPages) return;
  $("servidor").hidden = false;
  $("api").value = new URLSearchParams(location.search).get("api") || lembrar("api") || HUB_PADRAO;
  $("api").required = true;
  $("api").onchange = aoMudar;
}

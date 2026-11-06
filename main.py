# -*- coding: utf-8 -*-
"""
==========================================================
  SALVE A MASCOTE GIGIL
  Jogo 2D de aventura e exploração feito com Python + Pygame
==========================================================

Como rodar (VS Code / Windows):
    pip install pygame
    python main.py

Arquivos esperados (tudo que for opcional tem uma alternativa desenhada
pelo próprio jogo, então ele nunca fecha por falta de imagem ou som):

    main.py
    assets/jogador_sheet.png   (spritesheet do jogador - opcional)
    assets/jogador.png         (imagem simples do jogador - alternativa)
    assets/gigil.png           (a mascote GIGIL)
    assets/bateria.png         (as baterias coletáveis)
    assets/sounds/             (opcional) coleta, cela, resgate, terminal,
                               erro, saida, vitoria, porta, laser, late,
                               clique  e  musica  (.wav, .ogg ou .mp3).
                               Sem arquivos, o jogo gera os sons sozinho.

Controles:
    WASD / Setas ... mover          E ...... interagir
    Esc ............ pausa          M ...... ligar/desligar o som
    F11 ............ tela cheia     R ...... jogar de novo (tela final)

Opções rápidas ficam logo abaixo (USAR_FASE_3, ESCALA_JOGADOR...).
"""

import math
import os
import random
from array import array
from collections import deque

import pygame

pygame.init()

# ==========================================
# CONFIGURAÇÕES GERAIS
# ==========================================

LARGURA = 900
ALTURA = 600
FPS = 60

# ---- opções que você pode mudar à vontade ----
USAR_FASE_3 = True                     # False: o jogo termina depois da fase 2
GIGIL_IMAGEM_OLHA_PARA_DIREITA = True  # se a GIGIL andar "de costas", troque
ESCALA_JOGADOR = 1.0                   # tamanho do jogador (1.0 = tamanho original da spritesheet)
MOSTRAR_FPS = False                    # mostra os quadros por segundo no canto

# Tela de créditos (edite os nomes da equipe aqui)
CREDITOS = [
    ("SALVE A MASCOTE GIGIL", "titulo"),
    ("Projeto escolar de jogo 2D", "texto"),
    ("", "texto"),
    ("Programação e fases", "subtitulo"),
    ("(escreva aqui os nomes da equipe)", "texto"),
    ("", "texto"),
    ("Arte do personagem e da GIGIL", "subtitulo"),
    ("(escreva aqui quem desenhou)", "texto"),
    ("", "texto"),
    ("Feito com Python e Pygame", "texto"),
    ("Obrigado por jogar!", "subtitulo"),
]

PRETO = (20, 23, 32)
BRANCO = (245, 245, 245)
CINZA = (75, 85, 105)
AZUL = (45, 110, 190)
VERDE = (50, 190, 110)
VERMELHO = (220, 65, 75)
AMARELO = (245, 200, 65)
ROXO = (150, 95, 220)
CIANO = (65, 210, 220)
LARANJA = (240, 150, 60)
CINZA_CLARO = (160, 172, 192)

# Organização da tela (900 x 600)
BARRA_TOPO = 30                 # faixa do HUD em cima
BARRA_BASE = 540                # a faixa de mensagens começa aqui
ALTURA_PAREDE = 74              # parede do fundo do laboratório
ARENA_PADRAO = (20, 104, 860, 432)

# Tamanhos das "pegadas" (hitbox no chão) do jogador e da GIGIL
JOGADOR_L, JOGADOR_A = 26, 16
GIGIL_L, GIGIL_A = 30, 20

tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.RESIZABLE)
pygame.display.set_caption("Salve a Mascote GIGIL")

relogio = pygame.time.Clock()

# Superfície interna: mantém as coordenadas do jogo
# mesmo quando a janela muda de tamanho.
jogo = pygame.Surface((LARGURA, ALTURA))

try:
    PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    PASTA_BASE = os.getcwd()
PASTA_ASSETS = os.path.join(PASTA_BASE, "assets")
PASTA_SONS = os.path.join(PASTA_ASSETS, "sounds")


def criar_fonte(tamanho, negrito=False):
    return pygame.font.SysFont("arial,segoeui,verdana", tamanho, bold=negrito)


fonte = criar_fonte(22)
fonte_pequena = criar_fonte(16)
fonte_mini = criar_fonte(13)
fonte_barra = criar_fonte(19, True)
fonte_titulo = criar_fonte(34, True)
fonte_media = criar_fonte(27, True)
fonte_grande = criar_fonte(58, True)

# ==========================================
# FUNÇÕES UTILITÁRIAS
# ==========================================


def limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def lerp(a, b, t):
    return a + (b - a) * t


def distancia_pontos(ponto1, ponto2):
    return math.hypot(
        ponto1[0] - ponto2[0],
        ponto1[1] - ponto2[1]
    )


def distancia_ate_rect(ponto, ret):
    """Distância de um ponto até a borda de um retângulo (0 se estiver dentro)."""
    dx = max(ret.left - ponto[0], 0, ponto[0] - ret.right)
    dy = max(ret.top - ponto[1], 0, ponto[1] - ret.bottom)
    return math.hypot(dx, dy)


def tom(cor, fator):
    """Clareia (fator > 1) ou escurece (fator < 1) uma cor."""
    return (
        int(limitar(cor[0] * fator, 0, 255)),
        int(limitar(cor[1] * fator, 0, 255)),
        int(limitar(cor[2] * fator, 0, 255)),
    )


def misturar(cor1, cor2, t):
    t = limitar(t, 0.0, 1.0)
    return (
        int(lerp(cor1[0], cor2[0], t)),
        int(lerp(cor1[1], cor2[1], t)),
        int(lerp(cor1[2], cor2[2], t)),
    )


# ---------- texto ----------

_cache_textos = {}


def renderizar(texto, fonte_usada, cor):
    chave = (texto, id(fonte_usada), cor)
    imagem = _cache_textos.get(chave)
    if imagem is None:
        if len(_cache_textos) > 700:
            _cache_textos.clear()
        imagem = fonte_usada.render(texto, True, cor)
        _cache_textos[chave] = imagem
    return imagem


def desenhar_texto(texto, x, y, cor=BRANCO,
                   fonte_usada=None, alvo=None,
                   centro=False, sombra=True):
    """Desenha um texto (por padrão na superfície 'jogo').
    Com centro=True, o x é o centro do texto."""
    if fonte_usada is None:
        fonte_usada = fonte
    if alvo is None:
        alvo = jogo

    imagem_texto = renderizar(texto, fonte_usada, cor)
    x = int(x)
    y = int(y)
    if centro:
        x -= imagem_texto.get_width() // 2

    if sombra:
        alvo.blit(
            renderizar(texto, fonte_usada, (6, 8, 16)),
            (x + 1, y + 1)
        )

    alvo.blit(imagem_texto, (x, y))
    return imagem_texto.get_width()


def cortar_texto(texto, fonte_usada, largura_max):
    """Corta o texto com reticências se ele passar da largura permitida."""
    if fonte_usada.size(texto)[0] <= largura_max:
        return texto
    while len(texto) > 1 and fonte_usada.size(texto + "…")[0] > largura_max:
        texto = texto[:-1]
    return texto + "…"


def quebrar_texto(texto, fonte_usada, largura_max):
    """Divide um texto em várias linhas que cabem na largura dada."""
    linhas = []
    for paragrafo in texto.split("\n"):
        atual = ""
        for palavra in paragrafo.split(" "):
            teste = palavra if not atual else atual + " " + palavra
            if fonte_usada.size(teste)[0] <= largura_max or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return linhas


# ---------- painéis, brilhos e sombras ----------

_cache_paineis = {}


def desenhar_painel(alvo, ret, cor=(12, 18, 32), alpha=215,
                    borda=None, raio=10, largura_borda=2):
    ret = pygame.Rect(ret)
    chave = (ret.w, ret.h, cor, alpha, raio)
    imagem = _cache_paineis.get(chave)
    if imagem is None:
        imagem = pygame.Surface((ret.w, ret.h), pygame.SRCALPHA)
        pygame.draw.rect(
            imagem, (cor[0], cor[1], cor[2], alpha),
            imagem.get_rect(), border_radius=raio
        )
        _cache_paineis[chave] = imagem
    alvo.blit(imagem, ret.topleft)
    if borda is not None:
        pygame.draw.rect(
            alvo, borda, ret, largura_borda, border_radius=raio
        )


_cache_brilhos = {}


def obter_brilho(raio, cor, nivel):
    chave = (raio, cor, nivel)
    imagem = _cache_brilhos.get(chave)
    if imagem is None:
        imagem = pygame.Surface((raio * 2, raio * 2))
        for r in range(raio, 0, -2):
            k = ((1 - r / raio) ** 1.7) * (nivel / 8)
            pygame.draw.circle(
                imagem,
                (int(cor[0] * k), int(cor[1] * k), int(cor[2] * k)),
                (raio, raio), r
            )
        _cache_brilhos[chave] = imagem
    return imagem


def desenhar_brilho(alvo, centro, raio, cor, intensidade=1.0):
    """Luz suave (soma a cor ao fundo). intensidade vai de 0 a 1."""
    nivel = int(limitar(intensidade, 0, 1) * 8)
    if nivel <= 0:
        return
    imagem = obter_brilho(raio, cor, nivel)
    alvo.blit(
        imagem, (int(centro[0]) - raio, int(centro[1]) - raio),
        special_flags=pygame.BLEND_RGB_ADD
    )


_cache_sombras = {}


def desenhar_sombra(alvo, centro_x, base_y, largura, altura=None, alpha=95):
    if altura is None:
        altura = max(6, largura // 3)
    chave = (int(largura), int(altura), alpha)
    imagem = _cache_sombras.get(chave)
    if imagem is None:
        imagem = pygame.Surface((chave[0], chave[1]), pygame.SRCALPHA)
        pygame.draw.ellipse(imagem, (0, 0, 0, alpha), imagem.get_rect())
        _cache_sombras[chave] = imagem
    alvo.blit(
        imagem, (int(centro_x - largura / 2), int(base_y - altura / 2))
    )


# ==========================================
# CARREGAMENTO DAS IMAGENS
# ==========================================


def carregar_imagem(nome):
    """Carrega uma imagem da pasta assets. Retorna None se não existir."""
    caminho = os.path.join(PASTA_ASSETS, nome)
    try:
        return pygame.image.load(caminho).convert_alpha()
    except (pygame.error, OSError):
        print(f"[aviso] Não encontrei '{nome}' em assets: "
              "vou usar um desenho no lugar.")
        return None


def carregar_sprites_gigil():
    """Carrega o spritesheet 5x5 de GIGIL em assets/gigil_spritesheet.png.
    A terceira linha contém os quadros laterais de caminhada e a última
    linha contém poses sentadas para usar como repouso.
    """
    imagem = carregar_imagem("gigil_spritesheet.png")
    if imagem is None:
        return None

    largura, altura = imagem.get_size()
    cel_w, cel_h = largura // 5, altura // 5

    def recortar(linha, coluna):
        celula = pygame.Rect(coluna * cel_w, linha * cel_h, cel_w, cel_h)
        quadro = imagem.subsurface(celula).copy()
        caixa = quadro.get_bounding_rect(min_alpha=12)
        if caixa.width <= 0 or caixa.height <= 0:
            return None
        quadro = quadro.subsurface(caixa).copy()
        escala = min(70 / quadro.get_width(), 58 / quadro.get_height())
        tamanho = (max(1, round(quadro.get_width() * escala)),
                   max(1, round(quadro.get_height() * escala)))
        return pygame.transform.smoothscale(quadro, tamanho)

    caminhada = [q for q in (recortar(2, c) for c in range(5)) if q]
    repouso = recortar(4, 2) or (caminhada[0] if caminhada else None)
    if not caminhada or repouso is None:
        print("[aviso] Não consegui recortar os sprites de GIGIL.")
        return None

    direita = caminhada
    esquerda = [pygame.transform.flip(q, True, False) for q in caminhada]
    parado_dir = repouso
    parado_esq = pygame.transform.flip(repouso, True, False)
    return {
        "quadros": {"direita": direita, "esquerda": esquerda,
                    "baixo": direita, "cima": esquerda},
        "parado": {"direita": parado_dir, "esquerda": parado_esq,
                   "baixo": parado_dir, "cima": parado_esq},
        "ancora": (repouso.get_width() // 2, repouso.get_height()),
    }


def ajustar_imagem(imagem, largura_max, altura_max):
    """Redimensiona mantendo a proporção para caber na caixa dada."""
    w, h = imagem.get_size()
    escala = min(largura_max / w, altura_max / h)
    novo = (max(1, round(w * escala)), max(1, round(h * escala)))
    return pygame.transform.smoothscale(imagem, novo)


def desenho_gigil_substituto():
    img = pygame.Surface((56, 56), pygame.SRCALPHA)
    pygame.draw.polygon(img, (120, 78, 40), [(8, 22), (4, 4), (22, 14)])
    pygame.draw.polygon(img, (120, 78, 40), [(48, 22), (52, 4), (34, 14)])
    pygame.draw.ellipse(img, (214, 160, 98), (6, 12, 44, 40))
    pygame.draw.circle(img, (30, 20, 20), (20, 28), 3)
    pygame.draw.circle(img, (30, 20, 20), (36, 28), 3)
    pygame.draw.ellipse(img, (40, 26, 26), (23, 35, 10, 7))
    return img


def desenho_bateria_substituto():
    img = pygame.Surface((36, 36), pygame.SRCALPHA)
    pygame.draw.rect(img, (60, 70, 90), (9, 6, 18, 28), border_radius=3)
    pygame.draw.rect(img, (225, 235, 245), (9, 6, 18, 28), 2, border_radius=3)
    pygame.draw.rect(img, (225, 235, 245), (14, 2, 8, 4))
    pygame.draw.rect(img, VERDE, (12, 18, 12, 13))
    pygame.draw.rect(img, VERDE, (12, 10, 12, 5))
    return img


def desenho_jogador_substituto():
    img = pygame.Surface((34, 66), pygame.SRCALPHA)
    pygame.draw.rect(img, (130, 82, 40), (7, 2, 20, 20), border_radius=4)
    pygame.draw.rect(img, (24, 40, 110), (5, 24, 24, 22), border_radius=3)
    pygame.draw.rect(img, (50, 56, 66), (8, 46, 8, 16))
    pygame.draw.rect(img, (50, 56, 66), (18, 46, 8, 16))
    pygame.draw.rect(img, BRANCO, (7, 62, 10, 3))
    pygame.draw.rect(img, BRANCO, (17, 62, 10, 3))
    return img


# ---------- spritesheet do jogador ----------
# A folha tem 5 colunas x 6 linhas de células 200x200.
# Ordem de leitura (0 = 1ª célula): 0-6 e 25 = de frente,
# 7-12 = de costas, 13-18 = olhando para a esquerda,
# 19-24 = olhando para a direita.

SHEET_CELULA = 200
SHEET_COLUNAS = 5
SHEET_RECORTE = pygame.Rect(40, 20, 80, 100)
SHEET_LINHA_SOMBRA = 105
SHEET_QUADROS = {
    "baixo": [0, 1, 2, 3, 4, 5, 6, 25],
    "cima": [7, 8, 9, 10, 11, 12],
    "esquerda": [13, 14, 15, 16, 17, 18],
    "direita": [19, 20, 21, 22, 23, 24],
}
SHEET_PARADO = {"baixo": 0, "cima": 7, "esquerda": 15, "direita": 21}
SHEET_NOMES = [
    "jogador_sheet.png", "jogador_sheet.jpg", "jogador_sheet.jpeg",
    "jogador_sprites.png", "jogador_sprites.jpg",
    "spritesheet.png", "spritesheet.jpg",
]


def procurar_spritesheet():
    """Acha a folha de sprites: primeiro pelos nomes conhecidos e,
    se não achar, por qualquer imagem da pasta com 1000x1200 pixels."""
    for nome in SHEET_NOMES:
        caminho = os.path.join(PASTA_ASSETS, nome)
        if os.path.exists(caminho):
            return caminho

    try:
        nomes = sorted(os.listdir(PASTA_ASSETS))
    except OSError:
        return None

    comuns = ("jogador.png", "gigil.png", "bateria.png")
    for nome in nomes:
        minusculo = nome.lower()
        if minusculo in comuns:
            continue
        if not minusculo.endswith((".png", ".jpg", ".jpeg")):
            continue
        caminho = os.path.join(PASTA_ASSETS, nome)
        try:
            tamanho = pygame.image.load(caminho).get_size()
        except (pygame.error, OSError):
            continue
        if tamanho == (SHEET_CELULA * SHEET_COLUNAS, SHEET_CELULA * 6):
            return caminho
    return None


def limpar_fundo_quadro(quadro):
    """Para folhas em .jpg: deixa transparente o fundo preto
    e a sombra cinza desenhada embaixo dos pés."""
    largura, altura = quadro.get_size()
    linha_sombra = SHEET_LINHA_SOMBRA - SHEET_RECORTE.y
    for y in range(altura):
        for x in range(largura):
            r, g, b, _ = quadro.get_at((x, y))
            maior = max(r, g, b)
            menor = min(r, g, b)
            fundo = maior < 30
            sombra = (
                y >= linha_sombra
                and 18 <= maior < 72
                and maior - menor < 16
            )
            if fundo or sombra:
                quadro.set_at((x, y), (0, 0, 0, 0))


def carregar_sprites_jogador():
    """Retorna um dicionário com os quadros de cada direção
    (ou None se a spritesheet não existir)."""
    caminho = procurar_spritesheet()
    if caminho is None:
        return None
    try:
        folha = pygame.image.load(caminho).convert_alpha()
    except (pygame.error, OSError):
        return None

    precisa_limpar = folha.get_at((0, 0))[3] > 0   # .jpg: fundo preto opaco

    brutos = {}
    for indice in range(26):
        linha, coluna = divmod(indice, SHEET_COLUNAS)
        area = pygame.Rect(
            coluna * SHEET_CELULA + SHEET_RECORTE.x,
            linha * SHEET_CELULA + SHEET_RECORTE.y,
            SHEET_RECORTE.w, SHEET_RECORTE.h
        )
        if (area.right > folha.get_width()
                or area.bottom > folha.get_height()):
            return None
        quadro = pygame.Surface(SHEET_RECORTE.size, pygame.SRCALPHA)
        quadro.blit(folha, (0, 0), area)
        if precisa_limpar:
            limpar_fundo_quadro(quadro)
        brutos[indice] = quadro

    uniao = None
    for quadro in brutos.values():
        caixa = quadro.get_bounding_rect()
        if caixa.w == 0:
            continue
        uniao = caixa if uniao is None else uniao.union(caixa)
    if uniao is None:
        return None

    caixa_frente = brutos[0].get_bounding_rect()
    ancora_x = caixa_frente.centerx - uniao.x
    ancora_y = uniao.h

    def preparar(indice):
        img = pygame.Surface(uniao.size, pygame.SRCALPHA)
        img.blit(brutos[indice], (0, 0), uniao)
        if ESCALA_JOGADOR != 1.0:
            img = pygame.transform.scale(
                img,
                (max(1, round(uniao.w * ESCALA_JOGADOR)),
                 max(1, round(uniao.h * ESCALA_JOGADOR)))
            )
        return img

    sprites = {"quadros": {}, "parado": {}}
    for direcao, indices in SHEET_QUADROS.items():
        sprites["quadros"][direcao] = [preparar(i) for i in indices]
        sprites["parado"][direcao] = preparar(SHEET_PARADO[direcao])
    sprites["ancora"] = (
        round(ancora_x * ESCALA_JOGADOR),
        round(ancora_y * ESCALA_JOGADOR)
    )
    sprites["altura"] = round(uniao.h * ESCALA_JOGADOR)
    return sprites


sprites_gigil = carregar_sprites_gigil()
_img_gigil = carregar_imagem("gigil.png")
_img_bateria = carregar_imagem("bateria.png")
_img_jogador = carregar_imagem("jogador.png")

if sprites_gigil is not None:
    gigil_base = sprites_gigil["parado"]["direita"]
elif _img_gigil is None:
    gigil_base = desenho_gigil_substituto()
else:
    gigil_base = ajustar_imagem(_img_gigil, 56, 56)

if _img_bateria is None:
    bateria_img = desenho_bateria_substituto()
else:
    bateria_img = ajustar_imagem(_img_bateria, 36, 36)

bateria_icone = ajustar_imagem(bateria_img, 22, 22)
bateria_icone_apagada = bateria_icone.copy()
bateria_icone_apagada.fill(
    (70, 70, 80, 255), special_flags=pygame.BLEND_RGBA_MULT
)

sprites_jogador = carregar_sprites_jogador()

if sprites_jogador is None:
    if _img_jogador is None:
        jogador_estatico = desenho_jogador_substituto()
    else:
        jogador_estatico = ajustar_imagem(_img_jogador, 40, 66)
    print("[aviso] Spritesheet do jogador não encontrada: "
          "usando a imagem simples.")

gigil_img_direita = gigil_base
gigil_img_esquerda = pygame.transform.flip(gigil_base, True, False)
if not GIGIL_IMAGEM_OLHA_PARA_DIREITA:
    gigil_img_direita, gigil_img_esquerda = (
        gigil_img_esquerda, gigil_img_direita
    )

# ==========================================
# VARIÁVEIS DO JOGO
# ==========================================

# ---- estado geral do programa ----
estado = "menu"        # menu, instrucoes, jogando, pausa, transicao,
#                        lendo, final, vitoria, creditos
rodando = True
tela_cheia = False
tamanho_janela = (LARGURA, ALTURA)

tempo = 0              # frames desde que o programa abriu (animações)
tempo_jogo = 0         # frames de jogo de verdade (cronômetro)
fase_atual = 1
venceu = False         # True quando o jogo inteiro foi concluído

velocidade_jogador = 4.8
velocidade_gigil = 3.6

# ---- mensagens e efeitos ----
mensagem = ""
mensagem_tempo = 0
cooldown_avisos = {}
banner = {"texto": "", "cor": BRANCO, "tempo": 0, "total": 1}
tremor_tempo = 0
tremor_forca = 0
particulas = []
aneis = []
textos_flutuantes = []

# ---- mundo e câmera ----
arena = pygame.Rect(*ARENA_PADRAO)
mundo_largura = LARGURA
mundo_altura = ALTURA
mundo = None
fundo_estatico = None
camera_x = 0.0
camera_y = 0.0

# ---- personagens ----
jogador = pygame.Rect(0, 0, JOGADOR_L, JOGADOR_A)
jogador_pos = [0.0, 0.0]
jogador_dir = "baixo"
jogador_movendo = False
jogador_anim = 0.0
jogador_piscar = 0         # pisca ao levar um choque

gigil = pygame.Rect(0, 0, GIGIL_L, GIGIL_A)
gigil_pos = [0.0, 0.0]
gigil_vel = [0.0, 0.0]
gigil_estado = "presa"     # presa, seguindo ou missao
gigil_segue = False
gigil_parada = False
gigil_caminho = []
gigil_timer_rota = 0
gigil_sem_rota = False
gigil_travada = 0
gigil_olhando = 1
gigil_anim = 0.0
gigil_missao = None
gigil_no_duto = False

# ---- cenário ----
obstaculos = []            # retângulos que bloqueiam (colisão)
blocos = []                # o desenho de cada obstáculo
portas = []
interativos = []
props_parede = []
cabos = []
registros_lidos = set()
saida = pygame.Rect(0, 0, 0, 0)
saida_aberta = False
energia_nivel = 0.0
checkpoints = []
ponto_retorno = (0, 0)

# ---- fase 1 ----
baterias = []
baterias_coletadas = 0
cela = pygame.Rect(0, 0, 0, 0)
porta_cela = None
cela_aberta = False
cela_timer = -1

# ---- fase 2 ----
terminais = []
terminais_ativados = [False, False, False]
ordem_terminais = [1, 0, 2]
progresso_terminal = 0
erros_sequencia = 0
terminal_erro = [0, 0, 0]
porta_laser = None
quadro_sequencia = pygame.Rect(0, 0, 0, 0)
alerta_erro = 0

# ---- fase 3 ----
nucleos = []
nucleos_coletados = 0
nucleos_instalados = 0
seguranca_ativa = True
interruptor_ativo = False
portao_aberto = False
console_central = None
lasers = []
portao_rect = pygame.Rect(0, 0, 0, 0)

# ---- menus e telas ----
menu_indice = 0
pausa_indice = 0
instrucoes_origem = "menu"
creditos_origem = "menu"
transicao = {"t": 0, "destino": 1, "feito": False}
registro_aberto = None
final_t = 0
vitoria_t = 0
audio_ligado = True



# ==========================================
# ÁUDIO: SONS E MÚSICA
# Se existir um arquivo em assets/sounds/ (nome.wav, .ogg ou .mp3),
# ele é usado. Se não existir, o jogo gera o som sozinho.
# Se o computador não tiver áudio, o jogo simplesmente fica mudo.
# ==========================================

TAXA_AUDIO = 22050
NOMES_SONS = [
    "coleta", "cela", "resgate", "terminal", "erro", "saida",
    "vitoria", "porta", "laser", "late", "clique",
]
VOLUMES_SONS = {
    "coleta": 0.30, "cela": 0.45, "resgate": 0.45, "terminal": 0.30,
    "erro": 0.35, "saida": 0.35, "vitoria": 0.40, "porta": 0.30,
    "laser": 0.30, "late": 0.40, "clique": 0.22,
}

audio_disponivel = False
audio_sintetico = False
sons = {}
canal_musica = None
musica_sintetica = None
musica_de_arquivo = False


def iniciar_audio():
    global audio_disponivel, audio_sintetico
    try:
        pygame.mixer.quit()
        try:
            pygame.mixer.init(TAXA_AUDIO, -16, 2, 512, allowedchanges=0)
        except TypeError:
            pygame.mixer.init(TAXA_AUDIO, -16, 2, 512)
        info = pygame.mixer.get_init()
        audio_disponivel = info is not None
        audio_sintetico = (
            info is not None and info[1] == -16 and info[2] == 2
        )
        if audio_disponivel:
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)   # canal 0 é só da música
    except Exception as erro:
        print("[aviso] Áudio indisponível, o jogo ficará mudo:", erro)
        audio_disponivel = False
        audio_sintetico = False


# ---------- síntese simples de sons ----------


def _tom(freq, duracao, forma="seno", freq_fim=None,
         queda=4.0, ataque=0.004):
    n = max(1, int(TAXA_AUDIO * duracao))
    f0 = freq
    f1 = freq if freq_fim is None else freq_fim
    fase = 0.0
    saida = []
    n_ataque = max(1, int(TAXA_AUDIO * ataque))
    for i in range(n):
        t = i / n
        fase += 2 * math.pi * (f0 + (f1 - f0) * t) / TAXA_AUDIO
        if forma == "quadrada":
            v = 1.0 if math.sin(fase) >= 0 else -1.0
        elif forma == "serra":
            v = 2.0 * ((fase / (2 * math.pi)) % 1.0) - 1.0
        elif forma == "ruido":
            v = random.uniform(-1.0, 1.0)
        else:
            v = math.sin(fase)
        env = math.exp(-queda * t)
        if i < n_ataque:
            env *= i / n_ataque
        if i > n - 100:
            env *= (n - i) / 100
        saida.append(v * env)
    return saida


def _juntar(*trechos):
    resultado = []
    for trecho in trechos:
        resultado.extend(trecho)
    return resultado


def _misturar(*trilhas):
    n = max(len(t) for t in trilhas)
    resultado = [0.0] * n
    for trilha in trilhas:
        for i, v in enumerate(trilha):
            resultado[i] += v
    return resultado


def _silencio(duracao):
    return [0.0] * int(TAXA_AUDIO * duracao)


def _criar_som(amostras, volume=0.5):
    pico = max(0.0001, max(abs(v) for v in amostras))
    escala = volume * 32000 / max(pico, 1.0)
    dados = array("h")
    for v in amostras:
        valor = int(v * escala)
        dados.append(valor)   # canal esquerdo
        dados.append(valor)   # canal direito
    return pygame.mixer.Sound(buffer=dados.tobytes())


def _latido():
    return _misturar(
        _tom(540, 0.14, "quadrada", 250, queda=7),
        _tom(1, 0.14, "ruido", queda=14)
    )


def _sintetizar_efeito(nome):
    if nome == "coleta":
        return _juntar(
            _tom(880, 0.07, "quadrada", queda=3),
            _tom(1320, 0.16, "quadrada", queda=6)
        )
    if nome == "cela":
        return _juntar(
            _misturar(
                _tom(90, 0.25, "serra", 45, queda=5),
                _tom(1, 0.25, "ruido", queda=8)
            ),
            _tom(440, 0.1, "quadrada", queda=4),
            _tom(660, 0.1, "quadrada", queda=4),
            _tom(880, 0.28, "quadrada", queda=5)
        )
    if nome == "resgate":
        return _juntar(
            _latido(), _silencio(0.07), _latido(), _silencio(0.08),
            _tom(660, 0.08, "seno"), _tom(880, 0.08, "seno"),
            _tom(1100, 0.22, "seno", queda=5)
        )
    if nome == "terminal":
        return _juntar(
            _tom(740, 0.08, "seno", queda=3),
            _tom(1110, 0.16, "seno", queda=5)
        )
    if nome == "erro":
        return _misturar(
            _tom(160, 0.38, "quadrada", 90, queda=2.5),
            _tom(163, 0.38, "quadrada", 92, queda=2.5)
        )
    if nome == "saida":
        return _juntar(
            _tom(523, 0.09, "quadrada", queda=3),
            _tom(659, 0.09, "quadrada", queda=3),
            _tom(784, 0.09, "quadrada", queda=3),
            _tom(1046, 0.30, "quadrada", queda=4)
        )
    if nome == "vitoria":
        partes = []
        for freq, dur in ((523, 0.13), (523, 0.13), (523, 0.13),
                          (659, 0.30), (587, 0.14), (659, 0.14),
                          (784, 0.60)):
            partes.append(_misturar(
                _tom(freq, dur, "quadrada", queda=2),
                _tom(freq * 2, dur, "seno", queda=2)
            ))
        return _juntar(*partes)
    if nome == "porta":
        return _misturar(
            _tom(1, 0.35, "ruido", queda=6),
            _tom(200, 0.35, "serra", 120, queda=5)
        )
    if nome == "laser":
        return _misturar(
            _tom(1800, 0.2, "quadrada", 300, queda=7),
            _tom(1, 0.2, "ruido", queda=9)
        )
    if nome == "late":
        return _latido()
    return _tom(1000, 0.04, "quadrada", queda=8)   # clique


def _sintetizar_musica():
    """Ambiente de laboratório: acordes lentos, baixo e arpejo (~11 s)."""
    batida = 60.0 / 84
    n_compasso = int(4 * batida * TAXA_AUDIO)
    n_nota = n_compasso // 8
    acordes = [
        (220.00, 261.63, 329.63), (174.61, 220.00, 261.63),
        (261.63, 329.63, 392.00), (196.00, 246.94, 293.66),
    ]
    graves = [110.00, 87.31, 130.81, 98.00]
    ordem_arpejo = (0, 1, 2, 1, 0, 2, 1, 2)
    dois_pi = 2 * math.pi
    total = n_compasso * len(acordes)
    amostras = [0.0] * total

    for k, acorde in enumerate(acordes):
        inicio = k * n_compasso
        for freq in acorde:
            passo = dois_pi * freq / TAXA_AUDIO
            for i in range(n_compasso):
                env = math.sin(math.pi * i / n_compasso) ** 2
                amostras[inicio + i] += math.sin(passo * i) * env * 0.09

        passo = dois_pi * graves[k] / TAXA_AUDIO
        for i in range(n_compasso):
            env = math.exp(-1.0 * i / n_compasso)
            amostras[inicio + i] += math.sin(passo * i) * env * 0.16

        for j in range(8):
            freq = acorde[ordem_arpejo[j]] * 2
            passo = dois_pi * freq / TAXA_AUDIO
            comeco = inicio + j * n_nota
            for i in range(n_nota):
                env = math.exp(-6.0 * i / n_nota)
                amostras[comeco + i] += math.sin(passo * i) * env * 0.07
    return amostras


def _carregar_som_arquivo(nome):
    for extensao in (".wav", ".ogg", ".mp3"):
        caminho = os.path.join(PASTA_SONS, nome + extensao)
        if os.path.exists(caminho):
            try:
                return pygame.mixer.Sound(caminho)
            except (pygame.error, OSError):
                print(f"[aviso] Não consegui abrir o som {caminho}")
    return None


def carregar_audio():
    """Prepara todos os sons. Pode demorar um pouquinho na primeira vez."""
    global musica_sintetica, musica_de_arquivo
    iniciar_audio()
    if not audio_disponivel:
        return

    for nome in NOMES_SONS:
        som = _carregar_som_arquivo(nome)
        if som is None and audio_sintetico:
            try:
                som = _criar_som(
                    _sintetizar_efeito(nome), VOLUMES_SONS.get(nome, 0.4)
                )
            except Exception as erro:
                print(f"[aviso] Não consegui criar o som '{nome}':", erro)
        if som is not None:
            sons[nome] = som

    for extensao in (".ogg", ".mp3", ".wav"):
        caminho = os.path.join(PASTA_SONS, "musica" + extensao)
        if os.path.exists(caminho):
            try:
                pygame.mixer.music.load(caminho)
                musica_de_arquivo = True
                break
            except (pygame.error, OSError):
                print(f"[aviso] Não consegui abrir a música {caminho}")

    if not musica_de_arquivo and audio_sintetico:
        try:
            musica_sintetica = _criar_som(_sintetizar_musica(), 0.5)
        except Exception as erro:
            print("[aviso] Não consegui criar a música:", erro)


def tocar(nome):
    if not audio_ligado or nome not in sons:
        return
    try:
        sons[nome].play()
    except pygame.error:
        pass


def iniciar_musica():
    global canal_musica
    if not audio_disponivel:
        return
    try:
        if musica_de_arquivo:
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)
            if not audio_ligado:
                pygame.mixer.music.pause()
        elif musica_sintetica is not None:
            if canal_musica is None:
                canal_musica = pygame.mixer.Channel(0)
            canal_musica.set_volume(0.5)
            canal_musica.play(musica_sintetica, loops=-1)
            if not audio_ligado:
                canal_musica.pause()
    except pygame.error:
        pass


def alternar_audio():
    """Liga ou desliga todo o som (tecla M ou menu)."""
    global audio_ligado
    audio_ligado = not audio_ligado
    try:
        if musica_de_arquivo:
            if audio_ligado:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()
        elif canal_musica is not None:
            if audio_ligado:
                canal_musica.unpause()
            else:
                canal_musica.pause()
    except pygame.error:
        pass
    if audio_ligado:
        tocar("clique")



# ==========================================
# MENSAGENS E EFEITOS VISUAIS
# ==========================================


def avisar(texto, duracao=320):
    """Mostra uma mensagem na faixa de baixo da tela."""
    global mensagem, mensagem_tempo
    mensagem = texto
    mensagem_tempo = duracao


def avisar_com_pausa(chave, texto, pausa=150):
    """Igual a avisar(), mas não repete a mesma mensagem toda hora."""
    if cooldown_avisos.get(chave, 0) <= 0:
        avisar(texto)
        cooldown_avisos[chave] = pausa


def mostrar_banner(texto, cor=BRANCO, duracao=170):
    """Aviso grande e rápido no alto da tela (eventos importantes)."""
    banner["texto"] = texto
    banner["cor"] = cor
    banner["tempo"] = duracao
    banner["total"] = duracao


def tremer(forca=4, duracao=14):
    global tremor_tempo, tremor_forca
    tremor_tempo = duracao
    tremor_forca = forca


def criar_particulas(x, y, cor, quantidade=14, velocidade=3.0,
                     vida=34, tamanho=3, gravidade=0.05):
    for _ in range(quantidade):
        angulo = random.uniform(0, math.tau)
        vel = random.uniform(0.35, 1.0) * velocidade
        particulas.append([
            x, y,
            math.cos(angulo) * vel, math.sin(angulo) * vel - 0.4,
            vida + random.randint(-8, 8), vida,
            cor, tamanho, gravidade
        ])


def criar_anel(x, y, cor, raio_max=60, vida=26):
    aneis.append([x, y, 4.0, raio_max, cor, vida, vida])


def criar_texto_flutuante(texto, x, y, cor=BRANCO):
    textos_flutuantes.append([texto, x, y, 58, cor])


def efeito_brilho(x, y, cor=AMARELO, quantidade=16, raio=56):
    """Explosão de faíscas + anel: usado ao coletar e ativar coisas."""
    criar_particulas(x, y, cor, quantidade, 3.2)
    criar_anel(x, y, cor, raio)


def atualizar_efeitos():
    global tremor_tempo, mensagem_tempo

    for p in particulas:
        p[0] += p[2]
        p[1] += p[3]
        p[3] += p[8]
        p[2] *= 0.985
        p[4] -= 1
    particulas[:] = [p for p in particulas if p[4] > 0]

    for a in aneis:
        a[2] += (a[3] - a[2]) * 0.14
        a[5] -= 1
    aneis[:] = [a for a in aneis if a[5] > 0]

    for t in textos_flutuantes:
        t[2] -= 0.7
        t[3] -= 1
    textos_flutuantes[:] = [t for t in textos_flutuantes if t[3] > 0]

    if banner["tempo"] > 0:
        banner["tempo"] -= 1
    if tremor_tempo > 0:
        tremor_tempo -= 1
    if mensagem_tempo > 0:
        mensagem_tempo -= 1

    for chave in list(cooldown_avisos):
        cooldown_avisos[chave] -= 1
        if cooldown_avisos[chave] <= 0:
            del cooldown_avisos[chave]


def desenhar_efeitos_mundo(alvo):
    for a in aneis:
        k = a[5] / a[6]
        pygame.draw.circle(
            alvo, tom(a[4], 0.3 + 0.7 * k),
            (int(a[0]), int(a[1])), max(2, int(a[2])), 2
        )

    for p in particulas:
        k = p[4] / p[5]
        raio = max(1, int(p[7] * (0.4 + 0.6 * k)))
        pygame.draw.circle(
            alvo, p[6], (int(p[0]), int(p[1])), raio
        )

    for t in textos_flutuantes:
        cor = t[4] if t[3] > 14 else tom(t[4], t[3] / 14)
        desenhar_texto(
            t[0], t[1], t[2], cor, fonte_pequena,
            alvo=alvo, centro=True
        )


# ==========================================
# COLISÕES
# ==========================================


def solidos_atuais():
    """Tudo que bloqueia o movimento agora (obstáculos + portas fechadas)."""
    return obstaculos + [
        p["rect"] for p in portas if p["prog"] < 0.85
    ]


def solidos_para_busca():
    """O que a GIGIL considera parede ao procurar caminhos.
    Portas automáticas contam como livres (elas abrem sozinhas)."""
    return (
        obstaculos
        + [p["rect"] for p in portas
           if p["prog"] < 0.85 and not p["auto"]]
        + [laser["rect"] for laser in lasers]
    )


def mover_com_colisoes(retangulo, pos, dx, dy, solidos, limite):
    """Move o retângulo em dois passos (horizontal e depois vertical)
    e resolve as colisões com os obstáculos e com a arena.
    'pos' guarda a posição com casas decimais [x, y]."""
    # Movimento horizontal
    pos[0] += dx
    retangulo.x = round(pos[0])
    x_antes = retangulo.x

    for obstaculo in solidos:
        if retangulo.colliderect(obstaculo):
            if dx > 0:
                retangulo.right = obstaculo.left
            elif dx < 0:
                retangulo.left = obstaculo.right

    retangulo.clamp_ip(limite)
    if retangulo.x != x_antes:
        pos[0] = float(retangulo.x)

    # Movimento vertical
    pos[1] += dy
    retangulo.y = round(pos[1])
    y_antes = retangulo.y

    for obstaculo in solidos:
        if retangulo.colliderect(obstaculo):
            if dy > 0:
                retangulo.bottom = obstaculo.top
            elif dy < 0:
                retangulo.top = obstaculo.bottom

    retangulo.clamp_ip(limite)
    if retangulo.y != y_antes:
        pos[1] = float(retangulo.y)


def empurrar_para_fora(retangulo, pos, solidos, limite):
    """Se algo (como uma porta) fechar em cima do personagem,
    empurra ele para o lado mais próximo que esteja livre."""
    for _ in range(6):
        indice = retangulo.collidelist(solidos)
        if indice == -1:
            break
        o = solidos[indice]
        opcoes = {
            "esq": retangulo.right - o.left,
            "dir": o.right - retangulo.left,
            "cima": retangulo.bottom - o.top,
            "baixo": o.bottom - retangulo.top,
        }
        lado = min(opcoes, key=opcoes.get)
        if lado == "esq":
            retangulo.right = o.left
        elif lado == "dir":
            retangulo.left = o.right
        elif lado == "cima":
            retangulo.bottom = o.top
        else:
            retangulo.top = o.bottom
    retangulo.clamp_ip(limite)
    pos[0] = float(retangulo.x)
    pos[1] = float(retangulo.y)


# ==========================================
# BUSCA DE CAMINHOS DA GIGIL (BFS em grade)
# A arena é dividida em células de 20x20. Uma célula é "livre" se a
# GIGIL cabe ali sem encostar em nada. O BFS acha o caminho mais curto
# entre duas células e depois o caminho é "esticado" para ficar reto.
# ==========================================

CELULA = 20
VIZINHOS = [
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
]

grade_colunas = 0
grade_linhas = 0
grade_livre = bytearray()
grade_assinatura = None


def centro_da_celula(coluna, linha):
    return (
        arena.x + coluna * CELULA + CELULA // 2,
        arena.y + linha * CELULA + CELULA // 2
    )


def celula_de(ponto):
    coluna = int((ponto[0] - arena.x) // CELULA)
    linha = int((ponto[1] - arena.y) // CELULA)
    return (
        limitar(coluna, 0, grade_colunas - 1),
        limitar(linha, 0, grade_linhas - 1)
    )


def celula_esta_livre(coluna, linha):
    return grade_livre[linha * grade_colunas + coluna] == 1


def reconstruir_grade():
    global grade_colunas, grade_linhas, grade_livre
    solidos = solidos_para_busca()
    grade_colunas = arena.width // CELULA
    grade_linhas = arena.height // CELULA
    livre = bytearray(grade_colunas * grade_linhas)
    teste = pygame.Rect(0, 0, GIGIL_L + 8, GIGIL_A + 8)

    for linha in range(grade_linhas):
        for coluna in range(grade_colunas):
            teste.center = centro_da_celula(coluna, linha)
            if (arena.contains(teste)
                    and teste.collidelist(solidos) == -1):
                livre[linha * grade_colunas + coluna] = 1
    grade_livre = livre


def atualizar_grade_se_preciso():
    """Refaz a grade quando uma porta muda de estado."""
    global grade_assinatura
    assinatura = (
        tuple(p["prog"] < 0.85 and not p["auto"] for p in portas),
        len(obstaculos),
    )
    if assinatura != grade_assinatura:
        reconstruir_grade()
        grade_assinatura = assinatura


def celula_livre_proxima(ponto, raio_max=5):
    coluna0, linha0 = celula_de(ponto)
    if celula_esta_livre(coluna0, linha0):
        return (coluna0, linha0)
    melhor = None
    melhor_dist = 10 ** 9
    for dl in range(-raio_max, raio_max + 1):
        for dc in range(-raio_max, raio_max + 1):
            coluna = coluna0 + dc
            linha = linha0 + dl
            if not (0 <= coluna < grade_colunas
                    and 0 <= linha < grade_linhas):
                continue
            if not celula_esta_livre(coluna, linha):
                continue
            dist = dc * dc + dl * dl
            if dist < melhor_dist:
                melhor_dist = dist
                melhor = (coluna, linha)
    return melhor


def linha_livre(c0, l0, c1, l1):
    """Todas as células entre as duas estão livres? (Bresenham)"""
    dc = abs(c1 - c0)
    dl = abs(l1 - l0)
    sc = 1 if c0 < c1 else -1
    sl = 1 if l0 < l1 else -1
    erro = dc - dl
    coluna, linha = c0, l0
    while True:
        if not celula_esta_livre(coluna, linha):
            return False
        if coluna == c1 and linha == l1:
            return True
        e2 = 2 * erro
        nova_coluna, nova_linha = coluna, linha
        if e2 > -dl:
            erro -= dl
            nova_coluna += sc
        if e2 < dc:
            erro += dc
            nova_linha += sl
        if nova_coluna != coluna and nova_linha != linha:
            # passo na diagonal: não pode "cortar" a quina de uma parede
            if not (celula_esta_livre(nova_coluna, linha)
                    and celula_esta_livre(coluna, nova_linha)):
                return False
        coluna, linha = nova_coluna, nova_linha


def suavizar_caminho(celulas):
    resultado = [celulas[0]]
    i = 0
    while i < len(celulas) - 1:
        j = min(len(celulas) - 1, i + 30)
        while j > i + 1 and not linha_livre(
                celulas[i][0], celulas[i][1],
                celulas[j][0], celulas[j][1]):
            j -= 1
        resultado.append(celulas[j])
        i = j
    return [centro_da_celula(c, l) for c, l in resultado]


def buscar_caminho(origem, destino):
    """Caminho (lista de pontos em pixels) da origem até o destino,
    desviando de tudo. Retorna None se não existir caminho."""
    inicio = celula_livre_proxima(origem)
    fim = celula_livre_proxima(destino)
    if inicio is None or fim is None:
        return None

    colunas = grade_colunas
    linhas = grade_linhas
    livre = grade_livre
    i0 = inicio[1] * colunas + inicio[0]
    i1 = fim[1] * colunas + fim[0]
    if i0 == i1:
        return [centro_da_celula(fim[0], fim[1])]

    anterior = [-2] * (colunas * linhas)
    anterior[i0] = -1
    fila = deque([i0])
    achou = False

    while fila:
        atual = fila.popleft()
        if atual == i1:
            achou = True
            break
        coluna = atual % colunas
        linha = atual // colunas
        for dc, dl in VIZINHOS:
            nc = coluna + dc
            nl = linha + dl
            if nc < 0 or nl < 0 or nc >= colunas or nl >= linhas:
                continue
            novo = nl * colunas + nc
            if anterior[novo] != -2 or not livre[novo]:
                continue
            if dc and dl and not (
                    livre[linha * colunas + nc]
                    and livre[nl * colunas + coluna]):
                continue
            anterior[novo] = atual
            fila.append(novo)

    if not achou:
        return None

    celulas = []
    atual = i1
    while atual != -1:
        celulas.append((atual % colunas, atual // colunas))
        atual = anterior[atual]
    celulas.reverse()
    return suavizar_caminho(celulas)


def caminho_livre_para_gigil(p0, p1):
    """A GIGIL consegue andar em linha reta de p0 até p1?"""
    dist = distancia_pontos(p0, p1)
    passos = max(1, int(dist // 8))
    teste = pygame.Rect(0, 0, GIGIL_L, GIGIL_A)
    solidos = solidos_para_busca()
    for i in range(passos + 1):
        t = i / passos
        teste.center = (
            int(p0[0] + (p1[0] - p0[0]) * t),
            int(p0[1] + (p1[1] - p0[1]) * t)
        )
        if teste.collidelist(solidos) != -1:
            return False
    return True



# ==========================================
# CENÁRIO DO LABORATÓRIO
# Cada fase tem um tema (cores). O fundo (piso + paredes) é desenhado
# uma vez só; o que se mexe ou pisca é desenhado a cada quadro.
# ==========================================

fonte_numero = criar_fonte(18, True)

TEMAS = {
    1: {"piso": (66, 82, 112), "parede": (44, 58, 86), "luz": CIANO,
        "semente": 11, "nome": "LABORATÓRIO NEXUS"},
    2: {"piso": (62, 66, 112), "parede": (46, 46, 92), "luz": ROXO,
        "semente": 22, "nome": "SALA DE SERVIDORES"},
    3: {"piso": (72, 78, 94), "parede": (52, 56, 74), "luz": LARANJA,
        "semente": 33, "nome": "NÚCLEO CENTRAL"},
}

# altura = quanto o objeto "sobe" no desenho (visual 3/4)
ESTILOS_BLOCO = {
    "servidor": {"topo": (52, 64, 94), "frente": (34, 42, 66),
                 "borda": (110, 132, 172), "altura": 44},
    "maquina": {"topo": (96, 104, 120), "frente": (64, 70, 88),
                "borda": (150, 160, 180), "altura": 38},
    "mesa": {"topo": (122, 134, 152), "frente": (84, 94, 112),
             "borda": (176, 188, 204), "altura": 26},
    "caixa": {"topo": (110, 102, 84), "frente": (80, 72, 58),
              "borda": (166, 146, 104), "altura": 28},
    "parede": {"topo": (72, 84, 112), "frente": (46, 56, 80),
               "borda": (112, 128, 162), "altura": 36},
    "grade": {"topo": (88, 98, 118), "frente": (150, 164, 188),
              "borda": (200, 212, 230), "altura": 30},
    "terminal": {"topo": (70, 62, 112), "frente": (30, 26, 56),
                 "borda": (150, 130, 220), "altura": 34},
    "pedestal": {"topo": (200, 208, 222), "frente": (130, 140, 158),
                 "borda": (240, 246, 255), "altura": 22},
    "console": {"topo": (80, 88, 108), "frente": (44, 50, 68),
                "borda": (170, 180, 200), "altura": 50},
}



def desenhar_saida(alvo):
    """Portal de saída das fases 1 e 2 (vermelho = trancado, verde = livre)."""
    r = saida
    aberta = saida_aberta
    cor = VERDE if aberta else VERMELHO
    pygame.draw.rect(alvo, (18, 24, 38), r, border_radius=8)
    pygame.draw.rect(alvo, tom(cor, 0.9), r, 3, border_radius=8)

    # setas que correm em direção à porta
    for k in range(3):
        deslocamento = ((tempo * 0.8) + k * 14) % 42
        x = r.x + 8 + deslocamento
        if x < r.right - 14:
            pygame.draw.polygon(
                alvo, tom(cor, 1.0 if aberta else 0.55),
                [(x, r.centery - 9), (x + 10, r.centery), (x, r.centery + 9)]
            )

    # porta na parede da direita
    porta_rect = pygame.Rect(arena.right, r.y - 6, mundo_largura - arena.right, r.h + 12)
    if aberta:
        pygame.draw.rect(alvo, (210, 255, 225), porta_rect)
        desenhar_brilho(alvo, r.center, 90, VERDE, 0.6)
    else:
        pygame.draw.rect(alvo, (60, 66, 88), porta_rect)
        pygame.draw.line(alvo, (30, 34, 50), porta_rect.midtop, porta_rect.midbottom, 2)
    pygame.draw.rect(alvo, (150, 160, 184), porta_rect, 1)

    lampada = (r.centerx, r.y - 14)
    cor_lampada = cor if (aberta or (tempo // 20) % 2 == 0) else tom(cor, 0.3)
    pygame.draw.circle(alvo, cor_lampada, lampada, 5)
    desenhar_texto(
        "SAÍDA", r.centerx, r.y - 40, cor, fonte_pequena,
        alvo=alvo, centro=True
    )


def desenhar_portao(alvo):
    """Portão principal da fase 3 (na parede do fundo)."""
    p = portao_rect
    topo = arena.y - ALTURA_PAREDE + 6
    moldura = pygame.Rect(p.x - 10, topo, p.w + 20, arena.y - topo)
    pygame.draw.rect(alvo, (22, 26, 40), moldura, border_radius=4)
    abertura = pygame.Rect(p.x, topo + 8, p.w, arena.y - topo - 8)

    prog = portao_prog
    if prog > 0:
        # luz do lado de fora aparecendo
        for yy in range(abertura.h):
            k = yy / max(1, abertura.h)
            cor_ceu = misturar((255, 236, 170), (255, 255, 255), k)
            pygame.draw.line(
                alvo, cor_ceu, (abertura.x, abertura.y + yy),
                (abertura.right - 1, abertura.y + yy)
            )
    metade = int(p.w / 2 * (1 - prog))
    for lado in (0, 1):
        x = abertura.x if lado == 0 else abertura.right - metade
        if metade > 1:
            pygame.draw.rect(alvo, (96, 106, 134), (x, abertura.y, metade, abertura.h))
            pygame.draw.rect(alvo, (150, 162, 190), (x, abertura.y, metade, abertura.h), 1)
            for yy in range(abertura.y + 8, abertura.bottom - 4, 12):
                pygame.draw.line(alvo, (70, 78, 102), (x + 3, yy), (x + metade - 4, yy))
    # faixas de perigo nas laterais
    for lado_x in (moldura.x, moldura.right - 8):
        for yy in range(moldura.y, moldura.bottom, 12):
            cor_faixa = AMARELO if ((yy - moldura.y) // 12) % 2 == 0 else (30, 30, 36)
            pygame.draw.rect(alvo, cor_faixa, (lado_x, yy, 8, min(12, moldura.bottom - yy)))

    if portao_aberto:
        cor = VERDE
    else:
        cor = VERMELHO if (tempo // 18) % 2 == 0 else tom(VERMELHO, 0.4)
    pygame.draw.rect(alvo, tom(cor, 0.5), (moldura.x, moldura.y - 5, moldura.w, 5))
    pygame.draw.rect(alvo, cor, (moldura.centerx - 22, moldura.y - 5, 44, 5))
    if portao_aberto:
        desenhar_brilho(alvo, (p.centerx, arena.y + 20), 110, (255, 225, 140), 0.55)
    desenhar_texto(
        "SAÍDA PRINCIPAL", p.centerx, moldura.y - 22, cor, fonte_mini,
        alvo=alvo, centro=True
    )


def desenhar_console(alvo):
    """Console central da fase 3 (recebe os 3 núcleos de energia)."""
    bloco = console_central
    desenhar_bloco(alvo, bloco)
    r = bloco["rect"]
    h_vis = bloco["altura"]
    for i in range(3):
        cx = r.x + 22 + i * ((r.w - 44) // 2)
        cy = r.bottom - h_vis + 6 + (h_vis - 14) // 2
        pygame.draw.circle(alvo, (24, 30, 46), (cx, cy), 9)
        if i < nucleos_instalados:
            pygame.draw.circle(alvo, CIANO, (cx, cy), 7)
            pygame.draw.circle(alvo, BRANCO, (cx, cy), 3)
            desenhar_brilho(alvo, (cx, cy), 26, CIANO, 0.7)
        else:
            if i < nucleos_coletados and (tempo // 14) % 2 == 0:
                cor_anel = AMARELO
            else:
                cor_anel = (100, 110, 140)
            pygame.draw.circle(alvo, cor_anel, (cx, cy), 9, 2)
    lampada = (r.centerx, r.y - h_vis - 6)
    cor = VERDE if not seguranca_ativa else (VERMELHO if (tempo // 18) % 2 == 0 else tom(VERMELHO, 0.4))
    pygame.draw.circle(alvo, cor, lampada, 5)
    desenhar_brilho(alvo, lampada, 40, cor, 0.5)


def desenhar_registro(alvo, bloco):
    """Documento do laboratório: um papel que flutua sobre o pedestal."""
    r = bloco["rect"]
    lido = bloco.get("id") in registros_lidos
    balanco = math.sin(tempo * 0.09 + r.x) * 3
    cx = r.centerx
    cy = int(r.y - bloco["altura"] - 14 + balanco)
    cor = (150, 160, 180) if lido else AMARELO
    if not lido:
        desenhar_brilho(alvo, (cx, cy), 30, AMARELO, 0.45)
    pygame.draw.rect(alvo, (236, 240, 248), (cx - 8, cy - 10, 16, 20), border_radius=2)
    pygame.draw.rect(alvo, cor, (cx - 8, cy - 10, 16, 20), 1, border_radius=2)
    for k in range(3):
        pygame.draw.line(alvo, cor, (cx - 5, cy - 5 + k * 5), (cx + 5, cy - 5 + k * 5))


# ==========================================
# CABOS COM ENERGIA CORRENDO
# ==========================================


def criar_cabo(pontos, cor=None):
    comprimento = 0
    for a, b in zip(pontos, pontos[1:]):
        comprimento += distancia_pontos(a, b)
    cabos.append({"pontos": pontos, "cor": cor, "comprimento": max(1, comprimento)})


def ponto_no_cabo(pontos, distancia):
    for a, b in zip(pontos, pontos[1:]):
        seg = distancia_pontos(a, b)
        if distancia <= seg:
            t = distancia / seg if seg else 0
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        distancia -= seg
    return pontos[-1]


def desenhar_cabo_estatico(alvo, cabo):
    pontos = cabo["pontos"]
    pygame.draw.lines(alvo, (18, 22, 34), False, pontos, 7)
    pygame.draw.lines(alvo, (48, 56, 78), False, pontos, 3)
    for ponto in pontos:
        pygame.draw.circle(alvo, (18, 22, 34), ponto, 4)


def desenhar_cabos_dinamicos(alvo):
    for cabo in cabos:
        cor = cabo["cor"] or TEMAS[fase_atual]["luz"]
        quantidade = 1 + int(energia_nivel * 3)
        for k in range(quantidade):
            distancia = (tempo * 1.5 + k * cabo["comprimento"] / quantidade) % cabo["comprimento"]
            x, y = ponto_no_cabo(cabo["pontos"], distancia)
            intensidade = 0.25 + 0.6 * energia_nivel
            desenhar_brilho(alvo, (x, y), 12, cor, intensidade)
            pygame.draw.circle(alvo, tom(cor, 1.2), (int(x), int(y)), 2)


# ==========================================
# FUNDO ESTÁTICO (piso, paredes, sombras)
# ==========================================


def desenhar_piso(alvo, tema):
    base = tema["piso"]
    gerador = random.Random(tema["semente"])
    lado = 40
    for ty in range(arena.y, arena.bottom, lado):
        for tx in range(arena.x, arena.right, lado):
            v = gerador.randint(-5, 5)
            cor = (
                limitar(base[0] + v, 0, 255),
                limitar(base[1] + v, 0, 255),
                limitar(base[2] + v, 0, 255),
            )
            w = min(lado, arena.right - tx)
            h = min(lado, arena.bottom - ty)
            pygame.draw.rect(alvo, cor, (tx, ty, w, h))
            pygame.draw.line(alvo, tom(cor, 1.16), (tx, ty), (tx + w - 1, ty))
            pygame.draw.line(alvo, tom(cor, 1.16), (tx, ty), (tx, ty + h - 1))
            pygame.draw.line(alvo, tom(cor, 0.72), (tx, ty + h - 1), (tx + w - 1, ty + h - 1))
            pygame.draw.line(alvo, tom(cor, 0.72), (tx + w - 1, ty), (tx + w - 1, ty + h - 1))
            for rx, ry in ((tx + 4, ty + 4), (tx + w - 5, ty + 4),
                           (tx + 4, ty + h - 5), (tx + w - 5, ty + h - 5)):
                alvo.set_at((rx, ry), tom(cor, 0.6))
            sorteio = gerador.random()
            if w >= 30 and h >= 30:
                if sorteio < 0.07:
                    for i in range(4):
                        pygame.draw.rect(
                            alvo, tom(cor, 0.6), (tx + 10, ty + 9 + i * 6, w - 20, 3)
                        )
                elif sorteio < 0.12:
                    pygame.draw.line(
                        alvo, tom(cor, 0.82),
                        (tx + 8, ty + 12), (tx + 20, ty + 26), 2
                    )


def desenhar_paredes(alvo, tema):
    base = tema["parede"]
    luz = tema["luz"]

    # parede do fundo
    alvo.fill(tom(base, 0.6), (0, 0, mundo_largura, arena.y))
    parede = pygame.Rect(0, arena.y - ALTURA_PAREDE, mundo_largura, ALTURA_PAREDE)
    alvo.fill(base, parede)
    for px in range(0, mundo_largura, 60):
        painel = pygame.Rect(px + 3, parede.y + 10, 54, ALTURA_PAREDE - 26)
        pygame.draw.rect(alvo, tom(base, 0.82), painel, border_radius=3)
        pygame.draw.rect(alvo, tom(base, 1.3), painel, 1, border_radius=3)
        for rx, ry in ((painel.x + 4, painel.y + 4), (painel.right - 5, painel.y + 4),
                       (painel.x + 4, painel.bottom - 5), (painel.right - 5, painel.bottom - 5)):
            pygame.draw.circle(alvo, tom(base, 1.6), (rx, ry), 1)
    pygame.draw.rect(alvo, tom(base, 0.45), (0, parede.y, mundo_largura, 7))
    pygame.draw.rect(alvo, (14, 18, 30), (0, arena.y - 12, mundo_largura, 12))
    pygame.draw.rect(alvo, tom(luz, 0.6), (0, arena.y - 8, mundo_largura, 3))

    # paredes laterais e de baixo
    for x0, x1 in ((0, arena.x), (arena.right, mundo_largura)):
        alvo.fill(tom(base, 0.62), (x0, arena.y, x1 - x0, mundo_altura - arena.y))
        for py in range(arena.y, mundo_altura, 40):
            pygame.draw.line(alvo, tom(base, 0.42), (x0, py), (x1, py))
    pygame.draw.rect(alvo, tom(luz, 0.5), (arena.x - 3, arena.y, 3, arena.h))
    pygame.draw.rect(alvo, tom(luz, 0.5), (arena.right, arena.y, 3, arena.h))
    alvo.fill(tom(base, 0.55), (0, arena.bottom, mundo_largura, mundo_altura - arena.bottom))
    pygame.draw.rect(alvo, tom(luz, 0.5), (arena.x, arena.bottom, arena.w, 3))


def desenhar_sombras_estaticas(alvo):
    camada = pygame.Surface((mundo_largura, mundo_altura), pygame.SRCALPHA)
    for bloco in blocos:
        r = bloco["rect"]
        pygame.draw.rect(camada, (0, 0, 0, 70), (r.x + 6, r.y + 4, r.w, r.h), border_radius=3)
    for i in range(16):
        alpha = int(110 * (1 - i / 16) ** 2)
        pygame.draw.line(camada, (0, 0, 0, alpha), (arena.x, arena.y + i), (arena.right - 1, arena.y + i))
        pygame.draw.line(camada, (0, 0, 0, alpha // 2), (arena.x, arena.bottom - 1 - i), (arena.right - 1, arena.bottom - 1 - i))
    for i in range(10):
        alpha = int(80 * (1 - i / 10) ** 2)
        pygame.draw.line(camada, (0, 0, 0, alpha), (arena.x + i, arena.y), (arena.x + i, arena.bottom - 1))
        pygame.draw.line(camada, (0, 0, 0, alpha), (arena.right - 1 - i, arena.y), (arena.right - 1 - i, arena.bottom - 1))
    alvo.blit(camada, (0, 0))


def desenhar_faixas_perigo(alvo, ret, largura_faixa=10):
    ret = pygame.Rect(ret)
    faixa = pygame.Surface(ret.size, pygame.SRCALPHA)
    faixa.fill((26, 26, 32, 215))
    for x in range(-ret.h, ret.w, largura_faixa * 2):
        pygame.draw.polygon(
            faixa, (AMARELO[0], AMARELO[1], AMARELO[2], 215),
            [(x, ret.h), (x + largura_faixa, ret.h),
             (x + largura_faixa + ret.h, 0), (x + ret.h, 0)]
        )
    alvo.blit(faixa, ret.topleft)
    pygame.draw.rect(alvo, (20, 20, 26), ret, 1)


def gerar_props_parede(tema):
    """Sorteia monitores, lâmpadas e respiros na parede do fundo."""
    props_parede.clear()
    gerador = random.Random(tema["semente"] + 5)
    topo = arena.y - ALTURA_PAREDE
    for px in range(60, mundo_largura - 60, 120):
        tipo = gerador.choice(["monitor", "monitor", "lampada", "respiro"])
        if tipo == "monitor":
            ret = pygame.Rect(px + 4, topo + 14, 52, 32)
        elif tipo == "lampada":
            ret = pygame.Rect(px + 20, topo + 14, 20, 12)
        else:
            ret = pygame.Rect(px + 6, topo + 14, 48, 30)
        props_parede.append({
            "tipo": tipo, "rect": ret, "sem": gerador.random() * 6.28,
            "cor": gerador.choice([CIANO, VERDE, AMARELO, LARANJA]),
        })


def desenhar_props_estaticos(alvo):
    for prop in props_parede:
        r = prop["rect"]
        if prop["tipo"] == "monitor":
            pygame.draw.rect(alvo, (16, 20, 30), r.inflate(6, 6), border_radius=4)
            pygame.draw.rect(alvo, (120, 134, 160), r.inflate(6, 6), 1, border_radius=4)
            pygame.draw.rect(alvo, (16, 20, 30), (r.centerx - 8, r.bottom + 3, 16, 5))
        elif prop["tipo"] == "lampada":
            pygame.draw.rect(alvo, (24, 28, 42), r.inflate(8, 6), border_radius=5)
            pygame.draw.rect(alvo, (120, 134, 160), r.inflate(8, 6), 1, border_radius=5)
        else:
            pygame.draw.rect(alvo, (20, 24, 36), r, border_radius=3)
            for yy in range(r.y + 5, r.bottom - 3, 6):
                pygame.draw.line(alvo, (70, 80, 104), (r.x + 4, yy), (r.right - 5, yy), 2)
            pygame.draw.rect(alvo, (120, 134, 160), r, 1, border_radius=3)


def desenhar_props_dinamicos(alvo):
    for prop in props_parede:
        r = prop["rect"]
        if prop["tipo"] == "monitor":
            pygame.draw.rect(alvo, (8, 24, 30), r)
            pontos = []
            for i in range(0, r.w, 4):
                y = r.centery + math.sin(tempo * 0.07 + i * 0.45 + prop["sem"]) * (r.h // 3)
                pontos.append((r.x + i, int(y)))
            if len(pontos) > 1:
                pygame.draw.lines(alvo, prop["cor"], False, pontos, 2)
            barra = r.y + int((tempo * 0.6 + prop["sem"] * 9) % r.h)
            pygame.draw.line(alvo, tom(prop["cor"], 0.5), (r.x, barra), (r.right - 1, barra))
        elif prop["tipo"] == "lampada":
            ligada = ((tempo // 40) + int(prop["sem"])) % 3 != 0
            cor = prop["cor"] if ligada else tom(prop["cor"], 0.25)
            pygame.draw.rect(alvo, cor, r, border_radius=4)
            if ligada:
                desenhar_brilho(alvo, r.center, 46, prop["cor"], 0.35)


def montar_cenario():
    """Cria o mundo e desenha o fundo estático da fase atual."""
    global mundo, fundo_estatico
    tema = TEMAS[fase_atual]
    mundo = pygame.Surface((mundo_largura, mundo_altura))
    fundo_estatico = pygame.Surface((mundo_largura, mundo_altura))
    fundo_estatico.fill((10, 14, 24))
    desenhar_piso(fundo_estatico, tema)
    decorar_chao_da_fase(fundo_estatico, tema)
    for cabo in cabos:
        desenhar_cabo_estatico(fundo_estatico, cabo)
    desenhar_paredes(fundo_estatico, tema)
    desenhar_sombras_estaticas(fundo_estatico)
    gerar_props_parede(tema)
    desenhar_props_estaticos(fundo_estatico)
    decorar_parede_da_fase(fundo_estatico, tema)



# ==========================================
# TEXTOS DO JOGO
# ==========================================

INFO_FASES = {
    1: {"titulo": "FASE 1", "nome": "RESGATE DA GIGIL",
        "dica": "Encontre as 3 baterias, abra a cela e resgate a GIGIL."},
    2: {"titulo": "FASE 2", "nome": "FUGA DO LABORATÓRIO",
        "dica": "Ative os terminais na ordem certa para liberar a saída."},
    3: {"titulo": "FASE 3", "nome": "NÚCLEO CENTRAL",
        "dica": "Reúna os 3 núcleos de energia e desligue o sistema de segurança."},
}

TITULOS_HUD = {
    1: "FASE 1 - RESGATE DA GIGIL",
    2: "FASE 2 - FUGA DO LABORATÓRIO",
    3: "FASE 3 - NÚCLEO CENTRAL",
}

REGISTROS = {
    "r1": ("REGISTRO 01 - CELA 03",
           "Laboratório Nexus, dia 112.\n"
           "A mascote GIGIL foi trancada na Cela 03 depois que o seu faro "
           "tecnológico descobriu o cofre secreto da diretoria. A tranca só "
           "abre com a energia de três baterias reserva espalhadas pelo "
           "laboratório. Quem as encontrar poderá libertá-la."),
    "r2": ("REGISTRO 02 - SALA DE SERVIDORES",
           "Aviso da manutenção:\n"
           "Se o sistema travar, os terminais precisam ser ativados na ordem "
           "2, 1 e 3. Um erro reinicia tudo. A porta de segurança tem um "
           "painel de manutenção dentro de um duto tão estreito que só um "
           "bichinho pequeno consegue alcançar."),
    "r3": ("REGISTRO 03 - NÚCLEO DE SEGURANÇA",
           "Procedimento de emergência:\n"
           "O sistema de segurança só desliga com três núcleos de energia: um "
           "na Ala Oeste, um na Ala Leste e um guardado no Cofre Sul. Cuidado "
           "com os lasers: eles ligam e desligam em intervalos regulares."),
    "r4": ("REGISTRO 04 - DIÁRIO DE UM CIENTISTA",
           "Eu sabia que a GIGIL era especial. Ela não é um experimento: é "
           "uma amiga. Se alguém ler isto, por favor, leve-a para fora e "
           "deixe que ela veja o céu."),
}

RAIO_INTERACAO = 52

# ==========================================
# PREPARAÇÃO COMUM A TODAS AS FASES
# Tudo que pertence a uma fase é zerado aqui, para que nada
# "vaze" de uma fase para a outra (nem depois de reiniciar).
# ==========================================


def preparar_nivel_comum(numero, largura_mundo=LARGURA,
                         altura_mundo=ALTURA, ret_arena=ARENA_PADRAO):
    global fase_atual, arena, mundo_largura, mundo_altura
    global obstaculos, blocos, portas, interativos, cabos, lasers
    global zonas_parede, saida, saida_aberta, energia_nivel
    global checkpoints, ponto_retorno
    global jogador_dir, jogador_movendo, jogador_anim, jogador_piscar
    global gigil_estado, gigil_segue, gigil_parada, gigil_caminho
    global gigil_timer_rota, gigil_sem_rota, gigil_travada
    global gigil_olhando, gigil_anim, gigil_missao, gigil_no_duto
    global mensagem, mensagem_tempo, grade_assinatura, tremor_tempo
    global baterias, baterias_coletadas, cela, porta_cela
    global cela_aberta, cela_timer
    global terminais, progresso_terminal, erros_sequencia, porta_laser
    global alerta_erro, quadro_sequencia
    global nucleos, nucleos_coletados, nucleos_instalados
    global seguranca_ativa, interruptor_ativo, portao_aberto, portao_prog
    global console_central, portao_rect, porta_leste, porta_cofre

    fase_atual = numero
    arena = pygame.Rect(*ret_arena)
    mundo_largura = largura_mundo
    mundo_altura = altura_mundo

    obstaculos = []
    blocos = []
    portas = []
    interativos = []
    cabos = []
    lasers = []
    zonas_parede = []
    checkpoints = []
    saida = pygame.Rect(0, 0, 0, 0)
    saida_aberta = False
    energia_nivel = 0.0
    ponto_retorno = (0, 0)

    jogador_dir = "baixo"
    jogador_movendo = False
    jogador_anim = 0.0
    jogador_piscar = 0

    gigil_estado = "presa"
    gigil_segue = False
    gigil_parada = False
    gigil_caminho = []
    gigil_timer_rota = 0
    gigil_sem_rota = False
    gigil_travada = 0
    gigil_olhando = 1
    gigil_anim = 0.0
    gigil_missao = None
    gigil_no_duto = False

    mensagem = ""
    mensagem_tempo = 0
    tremor_tempo = 0
    grade_assinatura = None
    particulas.clear()
    aneis.clear()
    textos_flutuantes.clear()
    cooldown_avisos.clear()
    banner["tempo"] = 0

    baterias = []
    baterias_coletadas = 0
    cela = pygame.Rect(0, 0, 0, 0)
    porta_cela = None
    cela_aberta = False
    cela_timer = -1

    terminais = []
    terminais_ativados[:] = [False, False, False]
    terminal_erro[:] = [0, 0, 0]
    progresso_terminal = 0
    erros_sequencia = 0
    porta_laser = None
    alerta_erro = 0
    quadro_sequencia = pygame.Rect(0, 0, 0, 0)

    nucleos = []
    nucleos_coletados = 0
    nucleos_instalados = 0
    seguranca_ativa = True
    interruptor_ativo = False
    portao_aberto = False
    portao_prog = 0.0
    console_central = None
    portao_rect = pygame.Rect(0, 0, 0, 0)
    porta_leste = None
    porta_cofre = None


def colocar_personagens(jx, jy, gx, gy):
    """Põe o jogador e a GIGIL com os pés nos pontos dados."""
    global jogador_pos, gigil_pos, gigil_vel
    jogador.midbottom = (jx, jy)
    gigil.midbottom = (gx, gy)
    jogador_pos = [float(jogador.x), float(jogador.y)]
    gigil_pos = [float(gigil.x), float(gigil.y)]
    gigil_vel = [0.0, 0.0]


def criar_registro(rect, ident):
    """Documento do laboratório (pedestal com um papel flutuando)."""
    bloco = criar_bloco(rect, "pedestal")
    bloco["id"] = ident
    interativos.append({
        "tipo": "registro", "rect": pygame.Rect(rect), "id": ident
    })


def criar_painel_gigil(nicho, efeito, ident):
    """Cria um nicho com painel de manutenção que só a GIGIL alcança.
    'nicho' é o retângulo (x, y, l, a) encostado na parede de cima."""
    nx, ny, nl, na = nicho
    meio = nx + nl // 2
    # paredes do nicho: sobra uma fresta de 24 px (só a GIGIL passa)
    criar_bloco((nx, ny, 12, na), "parede", altura=30)
    criar_bloco((nx + nl - 12, ny, 12, na), "parede", altura=30)
    criar_bloco((nx + 12, ny + na - 12, meio - 12 - (nx + 12), 12), "parede", altura=30)
    criar_bloco((meio + 12, ny + na - 12, nx + nl - 12 - (meio + 12), 12), "parede", altura=30)
    painel = {
        "tipo": "painel_gigil", "id": ident, "feito": False,
        "efeito": efeito,
        "rect": pygame.Rect(meio - 14, ny + na, 28, 44),
        "entrada": (meio, ny + na + 30),
        "rota": [(meio, ny + na + 6), (meio, ny + na - 14), (meio, ny + 30)],
        "tela": pygame.Rect(meio - 13, ny + 6, 26, 14),
        "fresta": pygame.Rect(meio - 12, ny + na - 12, 24, 12),
    }
    interativos.append(painel)
    return painel


def painel_gigil_da_fase():
    for obj in interativos:
        if obj["tipo"] == "painel_gigil":
            return obj
    return None


# ==========================================
# FASE 1: RESGATAR A GIGIL
# ==========================================


def iniciar_fase1():
    global baterias, cela, porta_cela, zonas_parede, saida

    preparar_nivel_comum(1)

    criar_bloco((190, 104, 46, 240), "servidor")
    criar_bloco((340, 280, 46, 256), "maquina")
    criar_bloco((500, 104, 46, 190), "servidor")
    criar_bloco((610, 380, 46, 156), "maquina")
    criar_bloco((690, 262, 96, 40), "caixa")
    criar_bloco((580, 104, 100, 34), "mesa")
    criar_bloco((60, 112, 56, 40), "caixa")
    criar_bloco((520, 480, 60, 40), "caixa")

    # A cela: paredes de grade + uma porta de campo de força
    cela = pygame.Rect(740, 104, 140, 120)
    criar_bloco((740, 104, 14, 36), "grade")
    criar_bloco((740, 192, 14, 32), "grade")
    criar_bloco((754, 212, 126, 12), "grade")
    porta_cela = criar_porta((740, 140, 14, 52), "campo", ident="cela")

    baterias = [
        pygame.Rect(262, 150, 40, 40),
        pygame.Rect(440, 440, 40, 40),
        pygame.Rect(632, 310, 40, 40),
    ]

    saida = pygame.Rect(822, 452, 58, 80)
    criar_registro((104, 420, 34, 26), "r1")

    criar_cabo([(300, 360), (300, 450), (210, 450), (210, 520)])

    zonas_parede = [pygame.Rect(cela.x + 6, arena.y - 72, cela.w - 12, 62)]

    colocar_personagens(70, 500, 812, 202)
    avisar("Encontre as três baterias.")

    montar_cenario()
    atualizar_grade_se_preciso()
    atualizar_camera(True)


# ==========================================
# FASE 2: FUGA DO LABORATÓRIO
# ==========================================


def iniciar_fase2():
    global terminais, ordem_terminais, porta_laser, quadro_sequencia
    global zonas_parede, saida, gigil_estado, gigil_segue

    preparar_nivel_comum(2)

    # servidores em zigue-zague: o jogador precisa planejar o caminho
    criar_bloco((230, 104, 46, 236), "servidor")
    criar_bloco((390, 300, 46, 236), "servidor")
    criar_bloco((550, 104, 46, 236), "servidor")
    criar_bloco((710, 300, 46, 236), "servidor")
    criar_bloco((40, 330, 56, 40), "caixa")

    terminais = []
    posicoes = [(84, 112, 60, 30), (466, 486, 60, 30), (792, 112, 60, 30)]
    for indice, ret in enumerate(posicoes):
        terminais.append(criar_bloco(ret, "terminal"))
        interativos.append({
            "tipo": "terminal", "rect": pygame.Rect(ret), "indice": indice
        })

    # painel de manutenção que só a GIGIL alcança (abre a porta de laser)
    criar_painel_gigil((618, 104, 74, 64), "laser", "duto_laser")

    porta_laser = criar_porta((710, 104, 46, 196), "laser", ident="laser")

    saida = pygame.Rect(822, 452, 58, 80)
    ordem_terminais = [1, 0, 2]      # terminal 2, depois 1, depois 3

    criar_registro((476, 112, 34, 26), "r2")

    criar_cabo([(114, 150), (114, 240), (200, 240), (200, 430), (330, 430), (330, 220), (413, 220)])
    criar_cabo([(496, 440), (496, 360), (640, 360), (640, 230)])
    criar_cabo([(822, 150), (822, 250), (780, 250), (780, 440)])

    quadro_sequencia = pygame.Rect(56, arena.y - 66, 160, 52)
    zonas_parede = [quadro_sequencia.inflate(14, 8)]

    colocar_personagens(62, 500, 112, 500)
    gigil_estado = "seguindo"
    gigil_segue = True
    avisar("Ative os terminais na ordem 2, 1 e 3. Aproxime-se e pressione E.")

    montar_cenario()
    atualizar_grade_se_preciso()
    atualizar_camera(True)


# ==========================================
# FASE 3: NÚCLEO CENTRAL (mapa grande, com câmera)
# ==========================================


def iniciar_fase3():
    global nucleos, console_central, portao_rect, porta_leste, porta_cofre
    global lasers, zonas_parede, saida, checkpoints, ponto_retorno
    global gigil_estado, gigil_segue

    preparar_nivel_comum(3, 1540, 924, (20, 104, 1500, 760))

    # paredes que dividem as salas
    criar_bloco((500, 104, 40, 236), "parede")
    criar_porta((500, 340, 40, 80), "auto", auto=True, ident="oeste")
    porta_leste = criar_porta((1000, 340, 40, 80), "trava", ident="leste")
    porta_cofre = criar_porta((730, 480, 80, 40), "cofre", ident="cofre")

    # sala central (hub)
    console_central = criar_bloco((720, 236, 100, 60), "console")
    interativos.append({
        "tipo": "console", "rect": pygame.Rect(720, 236, 100, 60)
    })
    criar_bloco((560, 120, 46, 100), "servidor")
    criar_bloco((934, 120, 46, 100), "servidor")
    criar_registro((640, 130, 34, 26), "r3")

    # ala oeste
    criar_bloco((130, 104, 46, 400), "servidor")
    criar_bloco((260, 400, 46, 464), "maquina")
    criar_bloco((390, 560, 100, 40), "mesa")
    criar_bloco((40, 640, 56, 40), "caixa")
    criar_bloco((380, 700, 56, 40), "caixa")
    criar_bloco((350, 112, 60, 30), "terminal")
    interativos.append({
        "tipo": "interruptor", "rect": pygame.Rect(350, 112, 60, 30)
    })
    criar_registro((60, 130, 34, 26), "r4")

    # ala leste
    criar_bloco((1130, 104, 46, 300), "servidor")
    criar_bloco((1230, 460, 46, 404), "maquina")
    criar_bloco((1340, 160, 100, 34), "mesa")
    criar_bloco((1340, 640, 180, 20), "parede")
    criar_bloco((1340, 660, 20, 40), "parede")
    criar_bloco((1340, 780, 20, 84), "parede")
    criar_painel_gigil((1420, 104, 74, 64), "cofre", "duto_cofre")

    # cofre (sul)
    criar_bloco((540, 560, 76, 200), "servidor")
    criar_bloco((934, 560, 66, 200), "servidor")
    criar_bloco((740, 760, 60, 40), "pedestal")
    criar_bloco((860, 790, 60, 40), "caixa")

    nucleos = [
        {"rect": pygame.Rect(50, 770, 40, 40), "ala": "oeste"},
        {"rect": pygame.Rect(1420, 780, 40, 40), "ala": "leste"},
        {"rect": pygame.Rect(750, 724, 40, 40), "ala": "cofre"},
    ]

    # lasers temporizados: ligam e desligam em ciclos
    lasers = [
        {"rect": pygame.Rect(1340, 700, 20, 80), "ciclo": 240, "ligado": 100, "inicio": 60},
        {"rect": pygame.Rect(616, 560, 318, 14), "ciclo": 210, "ligado": 80, "inicio": 0},
    ]

    portao_rect = pygame.Rect(710, 104, 120, 44)
    saida = pygame.Rect(0, 0, 0, 0)

    checkpoints = [
        (pygame.Rect(540, 104, 460, 376), (590, 440)),
        (pygame.Rect(300, 320, 200, 120), (450, 400)),
        (pygame.Rect(1040, 320, 130, 120), (1075, 400)),
        (pygame.Rect(1280, 680, 60, 120), (1310, 750)),
        (pygame.Rect(700, 520, 140, 40), (770, 540)),
    ]
    ponto_retorno = (590, 440)

    criar_cabo([(770, 300), (770, 440), (560, 440)])
    criar_cabo([(770, 300), (900, 300), (900, 400), (980, 400)])
    criar_cabo([(770, 440), (770, 470)])

    zonas_parede = [pygame.Rect(690, 30, 160, 74)]

    colocar_personagens(590, 440, 640, 440)
    gigil_estado = "seguindo"
    gigil_segue = True
    avisar("Reúna os 3 núcleos de energia e desligue o sistema de segurança.")

    montar_cenario()
    atualizar_grade_se_preciso()
    atualizar_camera(True)


def iniciar_fase(numero):
    if numero == 1:
        iniciar_fase1()
    elif numero == 2:
        iniciar_fase2()
    else:
        iniciar_fase3()


# ==========================================
# DECORAÇÃO ESTÁTICA DE CADA FASE
# ==========================================


def decorar_chao_da_fase(alvo, tema):
    if fase_atual == 1:
        interior = pygame.Rect(754, 104, 126, 108)
        pygame.draw.rect(alvo, (36, 44, 64), interior)
        for x in range(interior.x, interior.right, 14):
            pygame.draw.line(alvo, (50, 60, 86), (x, interior.y), (x, interior.bottom))
        for y in range(interior.y, interior.bottom, 14):
            pygame.draw.line(alvo, (50, 60, 86), (interior.x, y), (interior.right, y))
        desenhar_texto("CELA 03", interior.centerx, interior.y + 30, (84, 98, 130),
                       fonte_pequena, alvo=alvo, centro=True, sombra=False)
        desenhar_faixas_perigo(alvo, (716, 140, 22, 52))
        desenhar_faixas_perigo(alvo, (saida.x - 24, saida.y, 18, saida.h))
        pygame.draw.circle(alvo, (92, 112, 152), (70, 505), 26, 2)
        desenhar_texto("INÍCIO", 70, 494, (112, 132, 172), fonte_mini,
                       alvo=alvo, centro=True, sombra=False)
    elif fase_atual == 2:
        desenhar_faixas_perigo(alvo, (690, 104, 18, 196))
        desenhar_faixas_perigo(alvo, (saida.x - 24, saida.y, 18, saida.h))
        pygame.draw.circle(alvo, (96, 98, 150), (62, 505), 26, 2)
        for terminal in terminais:
            r = terminal["rect"]
            pygame.draw.rect(alvo, (50, 46, 90), (r.x - 8, r.bottom, r.w + 16, 46), border_radius=6)
            pygame.draw.rect(alvo, (90, 84, 150), (r.x - 8, r.bottom, r.w + 16, 46), 1, border_radius=6)
    else:
        # emblema no chão da sala central
        centro = (770, 340)
        for raio, largura in ((150, 3), (120, 1), (84, 2)):
            pygame.draw.circle(alvo, (92, 98, 118), centro, raio, largura)
        for k in range(8):
            angulo = k * math.pi / 4
            ponta = (int(centro[0] + math.cos(angulo) * 150),
                     int(centro[1] + math.sin(angulo) * 150))
            pygame.draw.line(alvo, (86, 92, 112), centro, ponta, 1)
        for ret in ((508, 340, 28, 80), (1004, 340, 28, 80), (730, 466, 80, 20)):
            desenhar_faixas_perigo(alvo, ret)
        desenhar_texto("< ALA OESTE", 556, 372, (120, 130, 156), fonte_pequena,
                       alvo=alvo, sombra=False)
        desenhar_texto("ALA LESTE >", 960, 372, (120, 130, 156), fonte_pequena,
                       alvo=alvo, centro=True, sombra=False)
        desenhar_texto("COFRE SUL", 770, 440, (120, 130, 156), fonte_pequena,
                       alvo=alvo, centro=True, sombra=False)
        pygame.draw.circle(alvo, (98, 108, 140), (590, 445), 26, 2)
        for painel in interativos:
            if painel["tipo"] == "painel_gigil":
                f = painel["fresta"]
                pygame.draw.rect(alvo, (20, 24, 36), f.inflate(8, 0))
        # área do cofre e da câmara: piso diferente
        pygame.draw.rect(alvo, (58, 62, 80), (556, 574, 430, 280), 0)
        pygame.draw.rect(alvo, (96, 104, 130), (556, 574, 430, 280), 2)
        pygame.draw.rect(alvo, (58, 62, 80), (1360, 660, 160, 204), 0)
        pygame.draw.rect(alvo, (96, 104, 130), (1360, 660, 160, 204), 2)

    # frestas dos dutos (fase 2 também)
    if fase_atual == 2:
        for painel in interativos:
            if painel["tipo"] == "painel_gigil":
                pygame.draw.rect(alvo, (20, 24, 36), painel["fresta"].inflate(8, 0))


def decorar_parede_da_fase(alvo, tema):
    if fase_atual == 3:
        desenhar_texto("NÚCLEO CENTRAL", 770, 38, (150, 160, 190), fonte_barra,
                       alvo=alvo, centro=True, sombra=False)


# ==========================================
# INTERAÇÕES (tecla E)
# ==========================================


def interativo_ativo(obj):
    tipo = obj["tipo"]
    if tipo == "terminal":
        return not terminais_ativados[obj["indice"]]
    if tipo == "painel_gigil":
        return not obj["feito"]
    if tipo == "interruptor":
        return not interruptor_ativo
    if tipo == "console":
        return seguranca_ativa
    return tipo == "registro"


def texto_interacao(obj):
    tipo = obj["tipo"]
    if tipo == "terminal":
        return f"Ativar terminal {obj['indice'] + 1}"
    if tipo == "painel_gigil":
        return "Mandar a GIGIL pelo duto"
    if tipo == "interruptor":
        return "Destravar a porta leste"
    if tipo == "console":
        if nucleos_coletados > nucleos_instalados:
            return "Instalar núcleos"
        return "Console de segurança"
    return "Ler registro"


def interativo_proximo():
    melhor = None
    melhor_dist = RAIO_INTERACAO + 1
    for obj in interativos:
        if not interativo_ativo(obj):
            continue
        dist = distancia_ate_rect(jogador.center, obj["rect"])
        if dist < melhor_dist:
            melhor = obj
            melhor_dist = dist
    return melhor


def interagir():
    """Chamada quando o jogador aperta E."""
    obj = interativo_proximo()
    if obj is None:
        if fase_atual == 2:
            avisar("Aproxime-se do terminal e pressione E.")
        return

    tipo = obj["tipo"]
    if tipo == "terminal":
        ativar_terminal(obj["indice"])
    elif tipo == "painel_gigil":
        enviar_gigil(obj)
    elif tipo == "interruptor":
        usar_interruptor()
    elif tipo == "console":
        usar_console()
    elif tipo == "registro":
        abrir_registro(obj["id"])


def abrir_registro(ident):
    global estado, registro_aberto
    registro_aberto = ident
    registros_lidos.add(ident)
    estado = "lendo"
    tocar("clique")


# ---------- terminais da fase 2 ----------


def ativar_terminal(indice):
    global progresso_terminal, erros_sequencia, alerta_erro, energia_nivel

    if terminais_ativados[indice]:
        avisar("Esse terminal já está ativo.")
        return

    esperado = ordem_terminais[progresso_terminal]
    centro = terminais[indice]["rect"].center

    if indice == esperado:
        terminais_ativados[indice] = True
        progresso_terminal += 1
        energia_nivel = progresso_terminal / 3
        efeito_brilho(centro[0], centro[1] - 24, VERDE)
        criar_texto_flutuante("OK!", centro[0], centro[1] - 50, VERDE)
        tocar("terminal")
        if progresso_terminal == 3:
            restaurar_sistema()
        else:
            avisar(
                f"Terminal {indice + 1} ativado! "
                "Continue na ordem correta (2, 1 e 3)."
            )
    else:
        # ordem errada: o progresso volta ao começo
        terminais_ativados[:] = [False, False, False]
        progresso_terminal = 0
        energia_nivel = 0.0
        erros_sequencia += 1
        terminal_erro[indice] = 45
        alerta_erro = 40
        efeito_brilho(centro[0], centro[1] - 24, VERMELHO)
        tocar("erro")
        tremer(3, 12)
        mostrar_banner("SEQUÊNCIA INCORRETA!", VERMELHO, 120)
        avisar("Sequência incorreta. Tente novamente: 2, 1 e 3.")


def restaurar_sistema():
    global saida_aberta
    saida_aberta = True
    tocar("saida")
    tremer(3, 14)
    mostrar_banner("SISTEMA RESTAURADO!", VERDE, 190)
    avisar("Sistema restaurado! Saída liberada! Leve a GIGIL até lá.")
    abrir_porta(porta_laser, som=False)
    efeito_brilho(saida.centerx, saida.centery, VERDE, 24, 80)


# ---------- GIGIL e os painéis do duto ----------


def enviar_gigil(painel):
    global gigil_estado, gigil_missao
    if gigil_estado != "seguindo":
        avisar("A GIGIL já está cuidando de outra coisa.")
        return
    gigil_estado = "missao"
    gigil_missao = {"painel": painel, "fase": "ir", "i": 0, "t": 0}
    tocar("late")
    avisar("GIGIL, vá até o painel!")


def concluir_painel(painel):
    painel["feito"] = True
    tela_ret = painel["tela"]
    efeito_brilho(tela_ret.centerx, tela_ret.centery, VERDE, 20, 60)
    tocar("terminal")
    if painel["efeito"] == "laser":
        abrir_porta(porta_laser)
        mostrar_banner("PORTA DE SEGURANÇA LIBERADA!", VERDE, 190)
        avisar("A GIGIL desligou o laser! O caminho está livre.")
    else:
        abrir_porta(porta_cofre)
        mostrar_banner("COFRE SUL DESTRAVADO!", VERDE, 190)
        avisar("A GIGIL destravou o cofre, na sala central!")
    tremer(2, 10)


# ---------- fase 3: interruptor, console, núcleos ----------


def usar_interruptor():
    global interruptor_ativo
    interruptor_ativo = True
    abrir_porta(porta_leste)
    tocar("terminal")
    mostrar_banner("PORTA LESTE DESTRAVADA!", VERDE, 180)
    avisar("Porta leste destravada! Ela fica na sala central.")
    ret = pygame.Rect(350, 112, 60, 30)
    efeito_brilho(ret.centerx, ret.centery, VERDE, 18, 56)


def usar_console():
    global nucleos_instalados, energia_nivel
    if nucleos_coletados == 0:
        avisar("O console precisa de 3 núcleos de energia (0/3).")
        return
    if nucleos_coletados > nucleos_instalados:
        nucleos_instalados = nucleos_coletados
        energia_nivel = nucleos_instalados / 3
        centro = console_central["rect"].center
        efeito_brilho(centro[0], centro[1] - 30, CIANO, 22, 70)
        tocar("terminal")
        if nucleos_instalados < 3:
            avisar(f"Núcleos instalados: {nucleos_instalados}/3.")
    elif nucleos_instalados < 3:
        avisar(f"Faltam {3 - nucleos_instalados} núcleos de energia.")
    if nucleos_instalados >= 3:
        desligar_seguranca()


def desligar_seguranca():
    global seguranca_ativa, portao_aberto, grade_assinatura
    seguranca_ativa = False
    portao_aberto = True
    lasers.clear()
    grade_assinatura = None
    tocar("saida")
    tremer(4, 20)
    mostrar_banner("SISTEMA DE SEGURANÇA DESLIGADO!", VERDE, 220)
    avisar("Sistema desligado! O portão principal abriu. Corra com a GIGIL!")


def laser_ligado(laser):
    if not seguranca_ativa:
        return False
    return (tempo_jogo + laser["inicio"]) % laser["ciclo"] < laser["ligado"]


def laser_avisando(laser):
    if not seguranca_ativa or laser_ligado(laser):
        return False
    posicao = (tempo_jogo + laser["inicio"]) % laser["ciclo"]
    return posicao >= laser["ciclo"] - 26


def zap_jogador():
    """Choque do laser: manda o jogador de volta ao último checkpoint."""
    global jogador_pos, jogador_piscar
    centro = jogador.center
    efeito_brilho(centro[0], centro[1] - 20, VERMELHO, 22)
    tocar("laser")
    tremer(5, 16)
    jogador.midbottom = ponto_retorno
    jogador_pos = [float(jogador.x), float(jogador.y)]
    jogador_piscar = 60
    avisar("Alerta! O laser te levou de volta ao último checkpoint.")


# ==========================================
# REGRAS DE CADA FASE (chamadas a cada quadro)
# ==========================================


def resgatar_gigil():
    global gigil_estado, gigil_segue, saida_aberta
    gigil_estado = "seguindo"
    gigil_segue = True
    saida_aberta = baterias_coletadas >= 3
    centro = gigil.center
    criar_particulas(centro[0], centro[1] - 30, (255, 130, 170), 18, 2.6, 46, 4, -0.03)
    efeito_brilho(centro[0], centro[1] - 20, VERDE, 14, 70)
    criar_texto_flutuante("GIGIL LIVRE!", centro[0], centro[1] - 70, VERDE)
    tocar("resgate")
    mostrar_banner("GIGIL RESGATADA!", VERDE, 190)
    avisar("GIGIL resgatada! Leve a GIGIL até a saída.")

def abrir_cela():
    global cela_aberta
    cela_aberta = True
    abrir_porta(porta_cela, som=False)
    tocar("cela")
    tremer(3, 16)
    r = porta_cela["rect"]
    efeito_brilho(r.centerx, r.centery - 10, VERDE, 26, 70)
    mostrar_banner("CELA ABERTA!", VERDE, 190)
    avisar("Cela aberta! Entre e resgate a GIGIL.")


def gigil_perto_do_jogador(limite=170):
    return distancia_pontos(gigil.center, jogador.center) <= limite


def atualizar_fase1():
    global baterias_coletadas, cela_timer, energia_nivel, saida_aberta

    # coletar baterias (cada uma some do mapa depois de coletada)
    for bateria in baterias[:]:
        if jogador.colliderect(bateria.inflate(8, 8)):
            baterias.remove(bateria)
            baterias_coletadas += 1
            energia_nivel = baterias_coletadas / 3
            efeito_brilho(bateria.centerx, bateria.centery - 14, AMARELO)
            criar_texto_flutuante("+1", bateria.centerx, bateria.centery - 44, AMARELO)
            tocar("coleta")
            if baterias_coletadas < 3:
                avisar(f"Bateria coletada: {baterias_coletadas}/3.")
            else:
                avisar("Bateria coletada: 3/3. Energia restaurada!")
                mostrar_banner("ENERGIA RESTAURADA!", AMARELO, 150)
                cela_timer = 55

    # depois de coletar as 3, a cela abre (com um pequeno suspense)
    if cela_timer > 0:
        cela_timer -= 1
        if cela_timer == 0 and baterias_coletadas >= 3 and not cela_aberta:
            abrir_cela()

    # a cela trancada não deixa chegar na GIGIL
    if (not cela_aberta
            and distancia_ate_rect(jogador.center, porta_cela["rect"]) < 22):
        avisar_com_pausa(
            "cela", "A cela está trancada. Colete as 3 baterias para abri-la!"
        )

    # resgate: só depois da cela aberta
    if (cela_aberta and not gigil_segue and porta_cela["prog"] >= 0.85
            and jogador.colliderect(gigil.inflate(30, 20))):
        resgatar_gigil()

    saida_aberta = baterias_coletadas >= 3 and gigil_segue

    if jogador.colliderect(saida):
        if baterias_coletadas < 3:
            avisar_com_pausa("saida", "Você precisa coletar as 3 baterias!")
        elif not gigil_segue:
            avisar_com_pausa("saida", "Resgate a GIGIL antes de sair!")
        elif not gigil_perto_do_jogador():
            avisar_com_pausa("saida", "Espere a GIGIL chegar até você!", 90)
        else:
            concluir_fase()


def atualizar_fase2():
    global alerta_erro, saida_aberta

    for i in range(3):
        if terminal_erro[i] > 0:
            terminal_erro[i] -= 1
    if alerta_erro > 0:
        alerta_erro -= 1

    saida_aberta = progresso_terminal >= 3

    if jogador.colliderect(saida):
        if progresso_terminal < 3:
            avisar_com_pausa("saida", "Ative os 3 terminais primeiro!")
        elif not gigil_perto_do_jogador():
            avisar_com_pausa("saida", "Espere a GIGIL chegar até você!", 90)
        else:
            concluir_fase()


def atualizar_fase3():
    global nucleos_coletados, portao_prog, ponto_retorno

    for nucleo in nucleos[:]:
        if jogador.colliderect(nucleo["rect"].inflate(8, 8)):
            nucleos.remove(nucleo)
            nucleos_coletados += 1
            r = nucleo["rect"]
            efeito_brilho(r.centerx, r.centery - 18, CIANO, 20, 64)
            criar_texto_flutuante("+1 NÚCLEO", r.centerx, r.centery - 50, CIANO)
            tocar("coleta")
            avisar(f"Núcleo de energia coletado: {nucleos_coletados}/3.")

    for zona, ponto in checkpoints:
        if zona.collidepoint(jogador.center):
            ponto_retorno = ponto

    for laser in lasers:
        if laser_ligado(laser) and jogador_piscar <= 0:
            if jogador.colliderect(laser["rect"]):
                zap_jogador()
                break

    if portao_aberto and portao_prog < 1.0:
        portao_prog = min(1.0, portao_prog + 0.012)

    if portao_aberto and portao_prog > 0.5 and jogador.colliderect(portao_rect):
        if gigil_perto_do_jogador():
            concluir_fase()
        else:
            avisar_com_pausa("saida", "Espere a GIGIL chegar até você!", 90)


def concluir_fase():
    """Passa para a próxima fase ou para o final do jogo."""
    if fase_atual == 1:
        iniciar_transicao(2)
    elif fase_atual == 2 and USAR_FASE_3:
        iniciar_transicao(3)
    else:
        iniciar_final()


# ==========================================
# OBJETIVO ATUAL (texto e ponto no mapa)
# ==========================================


def objetivo_atual():
    """Retorna (texto do objetivo, ponto do mapa que ele indica)."""
    if fase_atual == 1:
        if baterias:
            mais_perto = min(
                baterias, key=lambda b: distancia_pontos(jogador.center, b.center)
            )
            return (f"Encontre as 3 baterias ({baterias_coletadas}/3)",
                    mais_perto.center)
        if not cela_aberta:
            return ("A cela está abrindo...", porta_cela["rect"].center)
        if not gigil_segue:
            return ("Entre na cela e resgate a GIGIL", gigil.center)
        return ("Leve a GIGIL até a saída", saida.center)

    if fase_atual == 2:
        if progresso_terminal < 3:
            proximo = ordem_terminais[progresso_terminal]
            painel = painel_gigil_da_fase()
            if proximo == 2 and porta_laser["prog"] < 0.85 and painel:
                return ("Libere a porta de laser: mande a GIGIL pelo duto (E)",
                        painel["entrada"])
            return (f"Ative os terminais: 2, 1 e 3 ({progresso_terminal}/3)",
                    terminais[proximo]["rect"].center)
        return ("Leve a GIGIL até a saída", saida.center)

    pendentes = [n["ala"] for n in nucleos]
    painel = painel_gigil_da_fase()
    if "oeste" in pendentes:
        ponto = [n for n in nucleos if n["ala"] == "oeste"][0]["rect"].center
        return ("Ala Oeste: encontre o 1º núcleo de energia", ponto)
    if not interruptor_ativo:
        return ("Ala Oeste: ative o painel da porta leste", (380, 130))
    if not painel["feito"]:
        return ("Ala Leste: mande a GIGIL pelo duto (E)", painel["entrada"])
    if "leste" in pendentes:
        ponto = [n for n in nucleos if n["ala"] == "leste"][0]["rect"].center
        return ("Ala Leste: pegue o núcleo (cuidado com o laser)", ponto)
    if "cofre" in pendentes:
        ponto = [n for n in nucleos if n["ala"] == "cofre"][0]["rect"].center
        return ("Cofre Sul: pegue o último núcleo", ponto)
    if nucleos_instalados < 3:
        return ("Instale os 3 núcleos no console central",
                console_central["rect"].center)
    return ("Corra para o portão principal com a GIGIL!", portao_rect.center)



# ==========================================================
# FINAL RECONSTRUÍDO: inicialização, atualização e desenho
# O arquivo recebido não continha esta parte; foi reconstruída.
# ==========================================================

def criar_bloco(rect, tipo, altura=None):
    r = pygame.Rect(rect)
    estilo = ESTILOS_BLOCO.get(tipo, ESTILOS_BLOCO["parede"])
    bloco = {"rect": r, "tipo": tipo,
             "altura": int(altura if altura is not None else estilo["altura"])}
    blocos.append(bloco)
    # Pedestais e consoles também bloqueiam o movimento, como os demais objetos.
    obstaculos.append(r)
    return bloco


def criar_porta(rect, tipo="auto", auto=False, ident=None):
    r = pygame.Rect(rect)
    porta = {"rect": r, "tipo": tipo, "auto": bool(auto),
             "ident": ident, "prog": 0.0, "aberta": False}
    portas.append(porta)
    return porta


def abrir_porta(porta, som=True):
    if porta is None:
        return
    porta["aberta"] = True
    porta["prog"] = 1.0
    if som:
        tocar("porta")
    atualizar_grade_se_preciso()


def atualizar_camera(imediata=False):
    global camera_x, camera_y
    max_x = max(0, mundo_largura - LARGURA)
    max_y = max(0, mundo_altura - ALTURA)
    alvo_x = limitar(jogador.centerx - LARGURA / 2, 0, max_x)
    alvo_y = limitar(jogador.centery - ALTURA / 2, 0, max_y)
    if imediata:
        camera_x, camera_y = alvo_x, alvo_y
    else:
        camera_x = lerp(camera_x, alvo_x, 0.16)
        camera_y = lerp(camera_y, alvo_y, 0.16)


def desenhar_bloco(alvo, bloco):
    r = bloco["rect"]
    estilo = ESTILOS_BLOCO.get(bloco.get("tipo", "parede"), ESTILOS_BLOCO["parede"])
    h = bloco.get("altura", estilo["altura"])
    frente = pygame.Rect(r.x, r.y - h, r.w, r.h + h)
    pygame.draw.rect(alvo, estilo["frente"], frente, border_radius=3)
    pygame.draw.rect(alvo, estilo["topo"], (r.x, r.y - h, r.w, max(5, h)), border_radius=3)
    pygame.draw.rect(alvo, estilo["borda"], frente, 1, border_radius=3)
    pygame.draw.line(alvo, tom(estilo["borda"], 1.15),
                     (r.x + 3, r.y - h + 3), (r.right - 3, r.y - h + 3), 2)
    if bloco.get("tipo") == "terminal":
        pygame.draw.rect(alvo, CIANO if not terminal_erro[0] else VERMELHO,
                         (r.x + 8, r.y - h + 8, max(4, r.w - 16), 5),
                         border_radius=2)
    elif bloco.get("tipo") in ("servidor", "maquina"):
        for yy in range(r.y - h + 12, r.bottom - 4, 10):
            pygame.draw.line(alvo, (100, 120, 150), (r.x + 6, yy), (r.right - 6, yy), 1)


def iniciar_transicao(destino):
    global estado, transicao
    transicao = {"t": 0, "destino": destino, "feito": False}
    estado = "transicao"


def iniciar_final():
    global estado, venceu, final_t
    estado = "final"
    venceu = True
    final_t = 0
    tocar("vitoria")
    mostrar_banner("MISSÃO CONCLUÍDA!", VERDE, 240)


def atualizar_gigil():
    global gigil_pos, gigil_vel, gigil_anim, gigil_olhando
    if not gigil_segue or gigil_estado == "presa":
        return
    alvo = (jogador.centerx - 34, jogador.centery + 8)
    dx, dy = alvo[0] - gigil.centerx, alvo[1] - gigil.centery
    dist = math.hypot(dx, dy)
    if dist > 14:
        passo = min(velocidade_gigil, dist)
        vx, vy = dx / max(1, dist) * passo, dy / max(1, dist) * passo
        teste = gigil.copy()
        teste.x += round(vx)
        teste.y += round(vy)
        if not teste.collidelist(solidos_atuais()) == -1:
            # Tenta primeiro horizontal e depois vertical para contornar cantos.
            teste = gigil.copy()
            teste.x += round(vx)
            if teste.collidelist(solidos_atuais()) == -1:
                gigil.x = teste.x
            else:
                teste = gigil.copy()
                teste.y += round(vy)
                if teste.collidelist(solidos_atuais()) == -1:
                    gigil.y = teste.y
        else:
            gigil.x, gigil.y = teste.x, teste.y
        gigil_olhando = 1 if dx >= 0 else -1
        gigil_anim += 0.18
    gigil_pos = [float(gigil.x), float(gigil.y)]


def desenhar_personagens(alvo):
    # Desenha a GIGIL primeiro, para que o jogador possa aparecer à frente dela.
    img_g = gigil_img_direita if gigil_olhando >= 0 else gigil_img_esquerda
    r_g = img_g.get_rect(midbottom=(gigil.centerx, gigil.bottom + 2))
    desenhar_sombra(alvo, gigil.centerx, gigil.bottom, 30, 8)
    alvo.blit(img_g, r_g)
    desenhar_sombra(alvo, jogador.centerx, jogador.bottom, 28, 8)
    if sprites_jogador is not None:
        direcao = jogador_dir if jogador_dir in sprites_jogador["quadros"] else "baixo"
        quadros = sprites_jogador["quadros"][direcao]
        if jogador_movendo and quadros:
            imagem = quadros[int(jogador_anim) % len(quadros)]
        else:
            imagem = sprites_jogador["parado"].get(direcao, quadros[0] if quadros else jogador_estatico)
        ancora = sprites_jogador["ancora"]
        alvo.blit(imagem, (jogador.centerx - imagem.get_width() // 2,
                           jogador.bottom - ancora[1]))
    else:
        imagem = jogador_estatico
        alvo.blit(imagem, imagem.get_rect(midbottom=(jogador.centerx, jogador.bottom + 2)))


def desenhar_mundo():
    if mundo is None or fundo_estatico is None:
        return
    mundo.blit(fundo_estatico, (0, 0))
    desenhar_props_dinamicos(mundo)
    desenhar_cabos_dinamicos(mundo)

    for bloco in blocos:
        if bloco.get("tipo") == "pedestal" and bloco.get("id"):
            desenhar_bloco(mundo, bloco)
            desenhar_registro(mundo, bloco)
        elif bloco is console_central:
            desenhar_console(mundo)
        else:
            desenhar_bloco(mundo, bloco)

    for porta in portas:
        if porta["prog"] < 0.99:
            r = porta["rect"]
            cor = CIANO if porta["tipo"] in ("campo", "laser") else (120, 140, 170)
            pygame.draw.rect(mundo, (18, 24, 38), r)
            pygame.draw.rect(mundo, cor, r, 2)
            if porta["tipo"] in ("campo", "laser"):
                for yy in range(r.y + 3, r.bottom, 10):
                    pygame.draw.line(mundo, tom(cor, 0.8), (r.x + 2, yy), (r.right - 2, yy), 2)

    if fase_atual < 3:
        desenhar_saida(mundo)
    else:
        desenhar_portao(mundo)

    if fase_atual == 1:
        for bateria in baterias:
            desenhar_brilho(mundo, bateria.center, 25, AMARELO, 0.5)
            pygame.draw.rect(mundo, (30, 34, 45), bateria, border_radius=5)
            pygame.draw.rect(mundo, AMARELO, bateria.inflate(-8, -8), border_radius=3)
            pygame.draw.rect(mundo, BRANCO, (bateria.centerx - 3, bateria.y + 8, 6, 5))
    if fase_atual == 3:
        for nucleo in nucleos:
            r = nucleo["rect"]
            desenhar_brilho(mundo, r.center, 30, CIANO, 0.65)
            pygame.draw.circle(mundo, (25, 38, 58), r.center, 15)
            pygame.draw.circle(mundo, CIANO, r.center, 10, 3)
            pygame.draw.circle(mundo, BRANCO, r.center, 4)
        for laser in lasers:
            r = laser["rect"]
            if laser_ligado(laser):
                pygame.draw.rect(mundo, (255, 55, 80), r)
                desenhar_brilho(mundo, r.center, 36, VERMELHO, 0.6)
            elif laser_avisando(laser):
                pygame.draw.rect(mundo, AMARELO, r, 2)
    for obj in interativos:
        if obj["tipo"] == "registro":
            continue
        r = obj["rect"]
        if obj["tipo"] == "terminal":
            ativo = terminais_ativados[obj["indice"]]
            pygame.draw.rect(mundo, (30, 70, 70) if ativo else (40, 35, 75), r, border_radius=4)
            pygame.draw.rect(mundo, VERDE if ativo else ROXO, r, 2, border_radius=4)
            desenhar_texto(f"T{obj['indice']+1}", r.centerx, r.y - 22,
                           BRANCO, fonte_mini, alvo=mundo, centro=True)
        elif obj["tipo"] == "interruptor":
            pygame.draw.rect(mundo, VERDE if interruptor_ativo else AMARELO, r, border_radius=4)
            desenhar_texto("INTERRUPTOR", r.centerx, r.y - 20, BRANCO, fonte_mini, alvo=mundo, centro=True)
        elif obj["tipo"] == "painel_gigil":
            pygame.draw.rect(mundo, VERDE if obj["feito"] else CIANO, obj["tela"], border_radius=3)
            pygame.draw.rect(mundo, (15, 22, 35), obj["fresta"], 2)
        elif obj["tipo"] == "console":
            pass
    desenhar_personagens(mundo)
    desenhar_efeitos_mundo(mundo)


def desenhar_hud():
    pygame.draw.rect(jogo, (14, 19, 32), (0, 0, LARGURA, BARRA_TOPO))
    pygame.draw.line(jogo, TEMAS[fase_atual]["luz"], (0, BARRA_TOPO-1), (LARGURA, BARRA_TOPO-1), 2)
    desenhar_texto(TITULOS_HUD[fase_atual], 14, 6, BRANCO, fonte_pequena, alvo=jogo)
    if fase_atual == 1:
        progresso = f"BATERIAS {baterias_coletadas}/3"
    elif fase_atual == 2:
        progresso = f"TERMINAIS {progresso_terminal}/3"
    else:
        progresso = f"NÚCLEOS {nucleos_coletados}/3  INSTALADOS {nucleos_instalados}/3"
    desenhar_texto(progresso, LARGURA - 14, 6, AMARELO, fonte_pequena, alvo=jogo)
    objetivo, _ = objetivo_atual()
    pygame.draw.rect(jogo, (12, 17, 29), (0, BARRA_BASE, LARGURA, ALTURA - BARRA_BASE))
    desenhar_texto(cortar_texto(objetivo, fonte_pequena, LARGURA - 28),
                   14, BARRA_BASE + 8, CIANO, fonte_pequena, alvo=jogo)
    if mensagem and mensagem_tempo > 0:
        desenhar_texto(cortar_texto(mensagem, fonte_pequena, LARGURA - 28),
                       14, BARRA_BASE + 31, BRANCO, fonte_pequena, alvo=jogo)
    obj = interativo_proximo() if estado == "jogando" else None
    if obj:
        texto = "[E] " + texto_interacao(obj)
        largura = fonte_pequena.size(texto)[0] + 24
        desenhar_painel(jogo, pygame.Rect((LARGURA-largura)//2, ALTURA-76, largura, 30), alpha=220)
        desenhar_texto(texto, LARGURA//2, ALTURA-70, BRANCO, fonte_pequena, alvo=jogo, centro=True)
    if banner["tempo"] > 0:
        desenhar_painel(jogo, pygame.Rect(170, 72, 560, 48), alpha=225)
        desenhar_texto(banner["texto"], LARGURA//2, 84, banner["cor"], fonte_barra, alvo=jogo, centro=True)


def atualizar_jogo():
    global tempo_jogo, jogador_movendo, jogador_anim, jogador_dir, jogador_piscar
    tempo_jogo += 1
    if mensagem_tempo > 0:
        globals()["mensagem_tempo"] -= 1
    if banner["tempo"] > 0:
        banner["tempo"] -= 1
    if jogador_piscar > 0:
        jogador_piscar -= 1
    atualizar_efeitos()

    teclas = pygame.key.get_pressed()
    dx = (int(teclas[pygame.K_RIGHT] or teclas[pygame.K_d])
          - int(teclas[pygame.K_LEFT] or teclas[pygame.K_a]))
    dy = (int(teclas[pygame.K_DOWN] or teclas[pygame.K_s])
          - int(teclas[pygame.K_UP] or teclas[pygame.K_w]))
    jogador_movendo = bool(dx or dy)
    if dx and dy:
        dx *= 0.7071
        dy *= 0.7071
    if dx or dy:
        if abs(dx) > abs(dy):
            jogador_dir = "direita" if dx > 0 else "esquerda"
        else:
            jogador_dir = "baixo" if dy > 0 else "cima"
        jogador_anim += 0.22
        mover_com_colisoes(jogador, jogador_pos, dx * velocidade_jogador,
                           dy * velocidade_jogador, solidos_atuais(), arena)
    # Durante uma tarefa de duto, a IA de seguir o jogador não pode
    # sobrescrever o movimento roteirizado da GIGIL.

    for porta in portas:
        if porta["auto"] and not porta["aberta"] and jogador.colliderect(porta["rect"].inflate(18, 18)):
            abrir_porta(porta, som=False)
    atualizar_grade_se_preciso()
    if gigil_estado == "missao" and gigil_missao:
        atualizar_missao_gigil()
    else:
        atualizar_gigil()
    if fase_atual == 1:
        atualizar_fase1()
    elif fase_atual == 2:
        atualizar_fase2()
    else:
        atualizar_fase3()
    atualizar_camera()


def desenhar_menu(titulo, linhas, dica="ENTER para continuar"):
    jogo.fill((10, 15, 28))
    for i in range(24):
        x = (i * 47 + tempo * 2) % LARGURA
        y = (i * 83 + tempo) % ALTURA
        pygame.draw.circle(jogo, (35, 55, 82), (x, y), 2)
    desenhar_texto(titulo, LARGURA//2, 150, CIANO, fonte_titulo, alvo=jogo, centro=True)
    y = 230
    for linha in linhas:
        desenhar_texto(linha, LARGURA//2, y, BRANCO, fonte, alvo=jogo, centro=True)
        y += 36
    desenhar_texto(dica, LARGURA//2, 500, AMARELO, fonte_pequena, alvo=jogo, centro=True)


def executar():
    global rodando, estado, tempo, tela, jogo, tela_cheia, tamanho_janela
    global fase_atual, final_t, jogador_pos, gigil_pos, audio_ligado
    iniciar_audio()
    try:
        iniciar_musica()
    except Exception:
        pass
    while rodando:
        dt = relogio.tick(FPS)
        tempo += 1
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.VIDEORESIZE and not tela_cheia:
                tamanho_janela = evento.size
                tela = pygame.display.set_mode(tamanho_janela, pygame.RESIZABLE)
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_F11:
                    tela_cheia = not tela_cheia
                    tela = pygame.display.set_mode((0, 0), pygame.FULLSCREEN) if tela_cheia else pygame.display.set_mode(tamanho_janela, pygame.RESIZABLE)
                elif evento.key == pygame.K_m:
                    alternar_audio()
                elif estado == "menu":
                    if evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                        fase_atual = 1
                        iniciar_fase(1)
                        estado = "jogando"
                elif estado == "instrucoes":
                    if evento.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                        estado = instrucoes_origem
                elif estado == "jogando":
                    if evento.key == pygame.K_ESCAPE:
                        estado = "pausa"
                    elif evento.key == pygame.K_e:
                        interagir()
                elif estado == "pausa":
                    if evento.key == pygame.K_ESCAPE:
                        estado = "jogando"
                    elif evento.key == pygame.K_RETURN:
                        estado = "menu"
                elif estado == "transicao":
                    pass
                elif estado == "lendo":
                    if evento.key in (pygame.K_ESCAPE, pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                        estado = "jogando"
                elif estado == "final":
                    if evento.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                        venceu = False
                        fase_atual = 1
                        iniciar_fase(1)
                        estado = "jogando"
                    elif evento.key == pygame.K_ESCAPE:
                        rodando = False

        if estado == "jogando":
            atualizar_jogo()
        elif estado == "transicao":
            transicao["t"] += 1
            if transicao["t"] >= 45 and not transicao["feito"]:
                transicao["feito"] = True
                fase_atual = transicao["destino"]
                iniciar_fase(fase_atual)
                estado = "jogando"
        elif estado == "final":
            final_t += 1

        if estado in ("jogando", "pausa", "lendo"):
            desenhar_mundo()
            jogo.fill((10, 14, 24))
            area = pygame.Rect(int(camera_x), int(camera_y), LARGURA, ALTURA)
            jogo.blit(mundo, (0, 0), area)
            desenhar_hud()
            if estado == "pausa":
                desenhar_painel(jogo, pygame.Rect(210, 210, 480, 150), alpha=235)
                desenhar_texto("JOGO PAUSADO", LARGURA//2, 235, AMARELO, fonte_titulo, alvo=jogo, centro=True)
                desenhar_texto("ESC: continuar  |  ENTER: menu", LARGURA//2, 300, BRANCO, fonte_pequena, alvo=jogo, centro=True)
            elif estado == "lendo":
                ident = registro_aberto
                titulo, texto_reg = REGISTROS.get(ident, ("REGISTRO", ""))
                desenhar_painel(jogo, pygame.Rect(100, 100, 700, 390), alpha=245)
                desenhar_texto(titulo, LARGURA//2, 125, AMARELO, fonte_barra, alvo=jogo, centro=True)
                yy = 185
                for linha in quebrar_texto(texto_reg, fonte, 630):
                    desenhar_texto(linha, 140, yy, BRANCO, fonte, alvo=jogo)
                    yy += 32
                desenhar_texto("E / ENTER / ESC para fechar", LARGURA//2, 440, CIANO, fonte_pequena, alvo=jogo, centro=True)
        elif estado == "menu":
            desenhar_menu("SALVE A MASCOTE GIGIL",
                          ["Uma aventura no Laboratório Nexus",
                           "WASD / Setas: mover   |   E: interagir",
                           "Resgate a GIGIL e atravesse as três fases." ])
        elif estado == "transicao":
            desenhar_menu("FASE " + str(transicao["destino"]),
                          [INFO_FASES[transicao["destino"]]["nome"],
                           INFO_FASES[transicao["destino"]]["dica"]],
                          "Preparando laboratório...")
        elif estado == "final":
            desenhar_menu("VOCÊ CONSEGUIU!",
                          ["A GIGIL está livre!",
                           "O Laboratório Nexus foi deixado para trás.",
                           "R: jogar novamente   |   ESC: sair"])
        # Copia a superfície interna para a janela visível. Sem isto,
        # o Pygame atualiza a janela, mas ela permanece preta.
        largura_tela, altura_tela = tela.get_size()
        if (largura_tela, altura_tela) == (LARGURA, ALTURA):
            tela.blit(jogo, (0, 0))
        else:
            quadro = pygame.transform.scale(jogo, (largura_tela, altura_tela))
            tela.blit(quadro, (0, 0))
        pygame.display.flip()
    pygame.quit()

def desenhar_terminal_bloco(alvo, bloco, numero, ativo, erro_tempo=0,
                            cor_base=ROXO, indice=0):
    """Terminal com tela, número e lâmpada de estado (vermelha/verde)."""
    desenhar_bloco(alvo, bloco)
    r = bloco["rect"]
    h_vis = bloco["altura"]

    if ativo:
        cor = VERDE
    elif erro_tempo > 0:
        cor = VERMELHO if (erro_tempo // 5) % 2 == 0 else tom(VERMELHO, 0.45)
    else:
        cor = cor_base

    tela_ret = pygame.Rect(r.x + 8, r.bottom - h_vis + 5, r.w - 16, h_vis - 12)
    pygame.draw.rect(alvo, tom(cor, 0.4), tela_ret, border_radius=3)
    if not ativo:
        yy = tela_ret.y + int((tempo * 0.8 + indice * 9) % tela_ret.h)
        pygame.draw.line(
            alvo, tom(cor, 1.0), (tela_ret.x + 1, yy), (tela_ret.right - 2, yy)
        )
    desenhar_texto(
        str(numero), tela_ret.centerx, tela_ret.y + 1, BRANCO,
        fonte_numero, alvo=alvo, centro=True, sombra=False
    )
    desenhar_brilho(alvo, tela_ret.center, 36, cor, 0.7 if ativo else 0.3)

    lampada = (r.right - 7, r.y - h_vis + 7)
    if ativo:
        cor_lampada = VERDE
    else:
        cor_lampada = VERMELHO if (tempo // 25) % 2 == 0 else tom(VERMELHO, 0.4)
    pygame.draw.circle(alvo, cor_lampada, lampada, 4)
    pygame.draw.circle(alvo, BRANCO, lampada, 4, 1)



def desenhar_terminal(alvo, indice):
    """Terminais 1 e 2 da fase 2."""
    desenhar_terminal_bloco(
        alvo, terminais[indice], indice + 1, terminais_ativados[indice],
        terminal_erro[indice], ROXO, indice
    )



def desenhar_balao(alvo, x, y, texto, cor=BRANCO):
    """Balão de fala pequeno (a ponta fica em x, y)."""
    largura = fonte_pequena.size(texto)[0] + 14
    ret = pygame.Rect(int(x - largura / 2), int(y - 28), largura, 22)
    pygame.draw.rect(alvo, (14, 18, 32), ret, border_radius=8)
    pygame.draw.rect(alvo, cor, ret, 2, border_radius=8)
    pygame.draw.polygon(
        alvo, (14, 18, 32),
        [(int(x) - 5, ret.bottom - 1), (int(x) + 5, ret.bottom - 1), (int(x), ret.bottom + 7)]
    )
    pygame.draw.lines(
        alvo, cor, False,
        [(int(x) - 5, ret.bottom), (int(x), ret.bottom + 7), (int(x) + 5, ret.bottom)], 2
    )
    desenhar_texto(texto, x, ret.y + 2, cor, fonte_pequena,
                   alvo=alvo, centro=True, sombra=False)



def desenhar_duto(alvo, painel):
    """Nicho com painel dentro: só a GIGIL passa pela fresta de 24 px.
    Mostra o que há lá dentro (terminal 3, bateria ou relé)."""
    n = painel["nicho"]
    interior = pygame.Rect(n.x + 12, n.y, n.w - 24, n.h - 12)
    pygame.draw.rect(alvo, (16, 20, 32), interior)
    pygame.draw.rect(alvo, (46, 54, 80), interior, 1)

    tela_ret = painel["tela"]
    acao = painel["acao"]
    feito = painel["feito"]

    if acao == "terminal3":
        cor = VERDE if terminais_ativados[2] else ROXO
        pygame.draw.rect(alvo, tom(cor, 0.4), tela_ret, border_radius=3)
        pygame.draw.rect(alvo, cor, tela_ret, 2, border_radius=3)
        desenhar_texto("3", tela_ret.centerx, tela_ret.y - 2, BRANCO, fonte_numero,
                       alvo=alvo, centro=True, sombra=False)
        desenhar_brilho(alvo, tela_ret.center, 30, cor, 0.55 if terminais_ativados[2] else 0.3)
    elif acao == "bateria":
        pygame.draw.rect(alvo, (30, 38, 58), tela_ret, border_radius=3)
        pygame.draw.rect(alvo, CIANO, tela_ret, 1, border_radius=3)
        if not feito:
            balanco = math.sin(tempo * 0.1) * 2
            alvo.blit(bateria_img, (tela_ret.centerx - bateria_img.get_width() // 2,
                                    int(tela_ret.bottom + 4 + balanco)))
            desenhar_brilho(alvo, (tela_ret.centerx, tela_ret.bottom + 24), 30, AMARELO, 0.5)
    else:
        cor = VERDE if feito else CIANO
        pygame.draw.rect(alvo, tom(cor, 0.4), tela_ret, border_radius=3)
        pygame.draw.rect(alvo, cor, tela_ret, 2, border_radius=3)
        desenhar_texto("R", tela_ret.centerx, tela_ret.y - 2, BRANCO, fonte_numero,
                       alvo=alvo, centro=True, sombra=False)
        desenhar_brilho(alvo, tela_ret.center, 30, cor, 0.5)

    # a fresta (entrada do duto) e a seta que indica o caminho
    fresta = painel["fresta"]
    pygame.draw.rect(alvo, (10, 12, 20), fresta.inflate(8, 2))
    for k in range(3):
        pygame.draw.line(alvo, (70, 80, 108),
                         (fresta.x + 2, fresta.y + 2 + k * 4),
                         (fresta.right - 3, fresta.y + 2 + k * 4), 2)
    if not feito and gigil_estado != "missao":
        pulso = 0.5 + 0.5 * math.sin(tempo * 0.15)
        desenhar_brilho(alvo, (fresta.centerx, fresta.bottom + 6), 34, CIANO, 0.3 + 0.4 * pulso)
        seta_y = fresta.bottom + 18 + int(math.sin(tempo * 0.15) * 3)
        pygame.draw.polygon(
            alvo, CIANO,
            [(fresta.centerx - 7, seta_y + 6), (fresta.centerx + 7, seta_y + 6),
             (fresta.centerx, seta_y - 4)]
        )
        desenhar_texto("DUTO", fresta.centerx, fresta.bottom + 24, CIANO,
                       fonte_mini, alvo=alvo, centro=True)



def desenhar_item(alvo, item):
    """Cartão de acesso flutuando no chão."""
    r = item["rect"]
    fase = r.x * 0.017
    balanco = math.sin(tempo * 0.08 + fase) * 4
    cx = r.centerx
    base = r.bottom - 4
    cor = CORES_CARTAO.get(item["cor"], AMARELO)

    desenhar_sombra(alvo, cx, base, 28, alpha=80)
    centro = (cx, int(base - 24 - balanco))
    desenhar_brilho(alvo, centro, 42, cor, 0.5 + 0.3 * math.sin(tempo * 0.12 + fase))
    cartao = pygame.Rect(0, 0, 28, 19)
    cartao.center = centro
    pygame.draw.rect(alvo, tom(cor, 0.5), cartao.move(0, 2), border_radius=3)
    pygame.draw.rect(alvo, cor, cartao, border_radius=3)
    pygame.draw.rect(alvo, BRANCO, cartao, 1, border_radius=3)
    pygame.draw.rect(alvo, (240, 220, 120), (cartao.x + 4, cartao.y + 4, 8, 6), border_radius=1)
    pygame.draw.line(alvo, BRANCO, (cartao.x + 4, cartao.bottom - 5),
                     (cartao.right - 5, cartao.bottom - 5), 2)
    desenhar_texto("CARTÃO " + item["cor"].upper(), cx, centro[1] - 34, cor,
                   fonte_mini, alvo=alvo, centro=True)



def desenhar_laser(alvo, laser):
    r = laser["rect"]
    ligado = laser_ligado(laser)
    aviso = laser_avisando(laser)
    horizontal = r.w >= r.h
    if horizontal:
        pontas = [(r.x, r.centery), (r.right, r.centery)]
    else:
        pontas = [(r.centerx, r.y), (r.centerx, r.bottom)]

    for ponta in pontas:
        pygame.draw.circle(alvo, (58, 64, 88), ponta, 8)
        if ligado:
            cor_led = VERMELHO
        elif aviso and (tempo // 4) % 2 == 0:
            cor_led = AMARELO
        else:
            cor_led = (96, 44, 56)
        pygame.draw.circle(alvo, cor_led, ponta, 4)

    a = (pontas[0][0], pontas[0][1] - 12)
    b = (pontas[1][0], pontas[1][1] - 12)
    if ligado:
        faixa = pygame.Surface((max(1, r.w), max(1, r.h)), pygame.SRCALPHA)
        faixa.fill((255, 40, 70, 70))
        alvo.blit(faixa, r.topleft)
        pygame.draw.line(alvo, (255, 90, 110), a, b, 6)
        pygame.draw.line(alvo, (255, 225, 230), a, b, 2)
        comprimento = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
        for k in range(0, comprimento + 1, 64):
            t = k / max(1, comprimento)
            ponto = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            desenhar_brilho(alvo, ponto, 30, VERMELHO, 0.45)
    elif aviso and (tempo // 3) % 2 == 0:
        pygame.draw.line(alvo, (255, 210, 90), a, b, 2)



def plataforma_estado(plat):
    """(ativa, avisando): a plataforma aparece e some em ciclos."""
    posicao = (tempo_jogo + plat["inicio"]) % plat["ciclo"]
    ativa = posicao < plat["ligado"]
    return ativa, ativa and posicao > plat["ligado"] - 26



def desenhar_abismo(alvo, abismo):
    """Buraco de energia com plataformas que piscam (cai quem pisar no vazio)."""
    r = abismo["rect"]
    pygame.draw.rect(alvo, (6, 8, 18), r)
    deslocamento = int(tempo * 0.8) % 16
    for yy in range(r.y + deslocamento, r.bottom, 16):
        pygame.draw.line(alvo, (22, 40, 74), (r.x, yy), (r.right - 1, yy))
    for k in range(6):
        px = r.x + int((k * 71 + tempo * 0.9) % r.w)
        py = r.y + int((k * 37 + tempo * 0.5) % r.h)
        pygame.draw.circle(alvo, (60, 140, 220), (px, py), 2)
    pygame.draw.rect(alvo, (70, 110, 190), r, 2)

    for plat in abismo["plataformas"]:
        p = plat["rect"]
        ativa, aviso = plataforma_estado(plat)
        if ativa:
            piscar = aviso and (tempo // 3) % 2 == 0
            cor_topo = (150, 160, 180) if piscar else (110, 126, 156)
            pygame.draw.rect(alvo, (36, 44, 66), p.move(0, 5), border_radius=6)
            pygame.draw.rect(alvo, cor_topo, p, border_radius=6)
            pygame.draw.rect(alvo, CIANO if not piscar else AMARELO, p, 2, border_radius=6)
            pygame.draw.circle(alvo, CIANO, (p.x + 8, p.y + 8), 2)
            pygame.draw.circle(alvo, CIANO, (p.right - 9, p.bottom - 9), 2)
        else:
            pygame.draw.rect(alvo, (40, 60, 100), p, 1, border_radius=6)



def desenhar_sirenes(alvo):
    for x, y in sirenes:
        if alarme_ativo:
            pulso = 0.5 + 0.5 * math.sin(tempo * 0.18 + x * 0.01)
            desenhar_brilho(alvo, (x, y), 46, VERMELHO, 0.35 + 0.55 * pulso)
            cor = VERMELHO if pulso > 0.45 else tom(VERMELHO, 0.5)
            angulo = tempo * 0.12
            for k in range(2):
                a = angulo + k * math.pi
                pygame.draw.line(alvo, tom(VERMELHO, 0.9), (x, y),
                                 (int(x + math.cos(a) * 26), int(y + math.sin(a) * 9)), 2)
        else:
            cor = (60, 160, 100)
        pygame.draw.rect(alvo, (28, 32, 46), (x - 8, y + 2, 16, 8), border_radius=2)
        pygame.draw.circle(alvo, cor, (x, y), 6)
        pygame.draw.circle(alvo, BRANCO, (x, y), 6, 1)



_alarme_superficies = {}



def desenhar_alarme_tela(alvo):
    """Iluminação de emergência: escurece a tela e pulsa em vermelho."""
    if not alarme_ativo:
        return
    if not _alarme_superficies:
        escuro = pygame.Surface((LARGURA, ALTURA))
        escuro.fill((0, 0, 16))
        vermelho = pygame.Surface((LARGURA, ALTURA))
        vermelho.fill((255, 20, 36))
        vinheta = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        for i in range(0, 90, 5):
            alpha = int(150 * (1 - i / 90) ** 2)
            pygame.draw.rect(vinheta, (60, 0, 10, alpha),
                             (i, i, LARGURA - 2 * i, ALTURA - 2 * i), 5)
        _alarme_superficies["escuro"] = escuro
        _alarme_superficies["vermelho"] = vermelho
        _alarme_superficies["vinheta"] = vinheta
    pulso = 0.5 + 0.5 * math.sin(tempo * 0.1)
    _alarme_superficies["escuro"].set_alpha(50)
    alvo.blit(_alarme_superficies["escuro"], (0, 0))
    _alarme_superficies["vermelho"].set_alpha(int(12 + 30 * pulso))
    alvo.blit(_alarme_superficies["vermelho"], (0, 0))
    alvo.blit(_alarme_superficies["vinheta"], (0, 0))



def desenhar_painel_central(alvo):
    """Painel da central de segurança (fase 3): mostra os 3 terminais."""
    bloco = console_central
    desenhar_bloco(alvo, bloco)
    r = bloco["rect"]
    h_vis = bloco["altura"]
    for i in range(3):
        cx = r.x + 22 + i * ((r.w - 44) // 2)
        cy = r.bottom - h_vis + 6 + (h_vis - 14) // 2
        pygame.draw.circle(alvo, (24, 30, 46), (cx, cy), 9)
        if seg_ativos[i]:
            pygame.draw.circle(alvo, VERDE, (cx, cy), 7)
            pygame.draw.circle(alvo, BRANCO, (cx, cy), 3)
            desenhar_brilho(alvo, (cx, cy), 26, VERDE, 0.7)
        else:
            cor_anel = VERMELHO if (tempo // 20) % 2 == 0 else tom(VERMELHO, 0.4)
            pygame.draw.circle(alvo, cor_anel, (cx, cy), 9, 2)
    if alarme_ativo:
        cor = VERMELHO if (tempo // 18) % 2 == 0 else tom(VERMELHO, 0.45)
        texto = "SEGURANÇA ATIVA"
    else:
        cor = VERDE
        texto = "SEGURANÇA DESLIGADA"
    desenhar_texto(texto, r.centerx, r.y - h_vis - 20, cor, fonte_mini,
                   alvo=alvo, centro=True)



CENTRO_VISAO_Y = 285



def ler_direcao():
    teclas = pygame.key.get_pressed()
    dx = (int(bool(teclas[pygame.K_RIGHT] or teclas[pygame.K_d]))
          - int(bool(teclas[pygame.K_LEFT] or teclas[pygame.K_a])))
    dy = (int(bool(teclas[pygame.K_DOWN] or teclas[pygame.K_s]))
          - int(bool(teclas[pygame.K_UP] or teclas[pygame.K_w])))
    return dx, dy



def mover_jogador():
    global jogador_movendo, jogador_anim, jogador_dir
    dx, dy = ler_direcao()
    jogador_movendo = bool(dx or dy)
    if not jogador_movendo:
        return

    if dx and not dy:
        jogador_dir = "direita" if dx > 0 else "esquerda"
    elif dy and not dx:
        jogador_dir = "baixo" if dy > 0 else "cima"
    elif jogador_dir in ("esquerda", "direita"):
        jogador_dir = "direita" if dx > 0 else "esquerda"
    else:
        jogador_dir = "baixo" if dy > 0 else "cima"

    fator = 0.7071 if (dx and dy) else 1.0
    jogador_anim += 0.25
    mover_com_colisoes(
        jogador, jogador_pos,
        dx * fator * velocidade_jogador, dy * fator * velocidade_jogador,
        solidos_atuais(), arena
    )



DIST_PARAR = 66        # ela para a esta distância do jogador



DIST_SEGUIR = 104      # volta a andar quando o jogador passa daqui



DIST_MIN = 40          # se o jogador chegar mais perto, ela se afasta



gigil_dir = "baixo"



def aplicar_movimento_gigil():
    global gigil_anim, gigil_olhando, gigil_travada, gigil_dir
    antes_x, antes_y = gigil_pos
    mover_com_colisoes(
        gigil, gigil_pos, gigil_vel[0], gigil_vel[1], solidos_atuais(), arena
    )
    deslocado = math.hypot(gigil_pos[0] - antes_x, gigil_pos[1] - antes_y)
    velocidade = math.hypot(gigil_vel[0], gigil_vel[1])
    if velocidade > 0.6:
        gigil_anim += 0.22
        if abs(gigil_vel[0]) > 0.35:
            gigil_olhando = 1 if gigil_vel[0] > 0 else -1
        if abs(gigil_vel[0]) > abs(gigil_vel[1]):
            gigil_dir = "direita" if gigil_vel[0] > 0 else "esquerda"
        else:
            gigil_dir = "baixo" if gigil_vel[1] > 0 else "cima"
        if deslocado < 0.25:
            gigil_travada += 1
        else:
            gigil_travada = max(0, gigil_travada - 2)
    else:
        gigil_travada = max(0, gigil_travada - 1)



def dirigir_gigil(destino, vel_max, chegando=False):
    """Acelera suavemente em direção ao destino (sem movimentos bruscos)."""
    dx = destino[0] - gigil.centerx
    dy = destino[1] - gigil.centery
    dist = math.hypot(dx, dy)
    if dist < 0.5:
        alvo_vx = alvo_vy = 0.0
    else:
        vel = vel_max
        if chegando:
            vel *= limitar((dist - 4) / 40, 0.25, 1.0)
        alvo_vx = dx / dist * vel
        alvo_vy = dy / dist * vel
    gigil_vel[0] += (alvo_vx - gigil_vel[0]) * 0.18
    gigil_vel[1] += (alvo_vy - gigil_vel[1]) * 0.18
    aplicar_movimento_gigil()



def frear_gigil():
    gigil_vel[0] *= 0.7
    gigil_vel[1] *= 0.7
    if abs(gigil_vel[0]) < 0.05:
        gigil_vel[0] = 0.0
    if abs(gigil_vel[1]) < 0.05:
        gigil_vel[1] = 0.0
    aplicar_movimento_gigil()



def afastar_gigil():
    """O jogador chegou muito perto: ela dá um passinho para trás."""
    dx = gigil.centerx - jogador.centerx
    dy = gigil.centery - jogador.centery
    dist = math.hypot(dx, dy) or 1.0
    gigil_vel[0] = dx / dist * 1.4
    gigil_vel[1] = dy / dist * 1.4
    aplicar_movimento_gigil()



def teleportar_gigil(ponto, efeito=True):
    """Última saída para ela nunca ficar presa: aparece em um ponto livre."""
    global gigil_pos, gigil_caminho, gigil_travada
    if efeito:
        criar_particulas(gigil.centerx, gigil.centery - 10, (230, 240, 255), 10, 2.0, 24, 3, 0.0)
    gigil.center = (int(ponto[0]), int(ponto[1]))
    gigil_pos = [float(gigil.x), float(gigil.y)]
    gigil_vel[0] = gigil_vel[1] = 0.0
    gigil_caminho = []
    gigil_travada = 0
    if efeito:
        criar_particulas(gigil.centerx, gigil.centery - 10, (230, 240, 255), 10, 2.0, 24, 3, 0.0)



def socorrer_gigil_travada():
    """Se a GIGIL ficar presa por muito tempo, leva ela para perto do jogador."""
    if gigil_travada < 120:
        return
    c0, l0 = celula_de(jogador.center)
    melhor = None
    melhor_dist = 10 ** 9
    for dl in range(-9, 10):
        for dc in range(-9, 10):
            coluna = c0 + dc
            linha = l0 + dl
            if not (0 <= coluna < grade_colunas and 0 <= linha < grade_linhas):
                continue
            if not celula_esta_livre(coluna, linha):
                continue
            centro = centro_da_celula(coluna, linha)
            dist = distancia_pontos(centro, jogador.center)
            if dist < 60:
                continue
            if dist < melhor_dist and caminho_livre_para_gigil(centro, jogador.center):
                melhor_dist = dist
                melhor = centro
    if melhor is not None:
        teleportar_gigil(melhor)



def mover_gigil_ate(alvo, parar_a, vel_max):
    """Leva a GIGIL até 'alvo' desviando de tudo.
    Retorna 'chegou', 'movendo' ou 'sem_rota'."""
    global gigil_caminho, gigil_timer_rota, gigil_sem_rota
    dist = distancia_pontos(gigil.center, alvo)
    visao = dist < 360 and caminho_livre_para_gigil(gigil.center, alvo)

    if visao and dist <= parar_a:
        gigil_caminho = []
        gigil_sem_rota = False
        frear_gigil()
        return "chegou"

    if visao:
        gigil_caminho = []
        gigil_sem_rota = False
        destino = alvo
        if parar_a > 0 and dist > 0.01:
            k = parar_a / dist
            ponto = (alvo[0] + (gigil.centerx - alvo[0]) * k,
                     alvo[1] + (gigil.centery - alvo[1]) * k)
            if caminho_livre_para_gigil(gigil.center, ponto):
                destino = ponto
        dirigir_gigil(destino, vel_max, chegando=True)
        return "movendo"

    # sem visão direta: segue o caminho do BFS
    gigil_timer_rota -= 1
    if gigil_timer_rota <= 0 or not gigil_caminho:
        gigil_timer_rota = 20
        caminho = buscar_caminho(gigil.center, alvo)
        if caminho is None:
            gigil_caminho = []
            gigil_sem_rota = True
            frear_gigil()
            return "sem_rota"
        gigil_caminho = caminho
        gigil_sem_rota = False

    while (len(gigil_caminho) > 1
           and distancia_pontos(gigil.center, gigil_caminho[0]) < 12):
        gigil_caminho.pop(0)

    destino = gigil_caminho[0]
    ultimo = len(gigil_caminho) == 1
    if ultimo and distancia_pontos(gigil.center, destino) < 6:
        gigil_caminho = []
        gigil_timer_rota = 0
        frear_gigil()
        return "chegou" if dist <= parar_a + 50 else "movendo"
    dirigir_gigil(destino, vel_max, chegando=ultimo)
    return "movendo"



def seguir_jogador():
    global gigil_parada
    alvo = jogador.center
    dist = distancia_pontos(gigil.center, alvo)
    visao = dist < 360 and caminho_livre_para_gigil(gigil.center, alvo)

    if gigil_parada and visao and dist < DIST_SEGUIR:
        frear_gigil()
        if dist < DIST_MIN:
            afastar_gigil()
        return

    gigil_parada = False
    vel = velocidade_gigil + limitar((dist - 150) / 100, 0.0, 1.4)
    if mover_gigil_ate(alvo, DIST_PARAR, vel) == "chegou":
        gigil_parada = True



def mover_gigil_scriptado(ponto, velocidade=1.9):
    """Anda em linha reta até o ponto, sem colisão (dentro do duto)."""
    global gigil_pos, gigil_olhando, gigil_anim
    dx = ponto[0] - gigil.centerx
    dy = ponto[1] - gigil.centery
    dist = math.hypot(dx, dy)
    if dist <= velocidade:
        gigil.center = (int(ponto[0]), int(ponto[1]))
        gigil_pos = [float(gigil.x), float(gigil.y)]
        gigil_vel[0] = gigil_vel[1] = 0.0
        return True
    gigil_pos[0] += dx / dist * velocidade
    gigil_pos[1] += dy / dist * velocidade
    gigil.x = round(gigil_pos[0])
    gigil.y = round(gigil_pos[1])
    gigil_vel[0] = dx / dist * velocidade
    gigil_vel[1] = dy / dist * velocidade
    gigil_anim += 0.2
    if abs(dx) > 0.5:
        gigil_olhando = 1 if dx > 0 else -1
    return False



def terminar_missao_gigil():
    global gigil_estado, gigil_missao, gigil_no_duto
    global gigil_parada, gigil_caminho, gigil_timer_rota
    gigil_estado = "seguindo"
    gigil_missao = None
    gigil_no_duto = False
    gigil_parada = False
    gigil_caminho = []
    gigil_timer_rota = 0



def atualizar_missao_gigil():
    """Passo a passo: 1) vai até a entrada do duto (BFS), 2) entra pela
    fresta, 3) mexe no painel, 4) volta pelo mesmo caminho."""
    global gigil_no_duto
    m = gigil_missao
    painel = m["painel"]
    trajeto = [painel["entrada"]] + painel["rota"]
    m["t"] += 1

    if m["fase"] == "ir":
        resultado = mover_gigil_ate(painel["entrada"], 10, velocidade_gigil + 1.2)
        travou = resultado == "sem_rota" and m["t"] > 90
        if resultado == "chegou" or travou or m["t"] > 720:
            if resultado != "chegou":
                teleportar_gigil(painel["entrada"])      # solução de segurança
            m["fase"] = "entrar"
            m["i"] = 1
            m["t"] = 0
    elif m["fase"] == "entrar":
        gigil_no_duto = True
        if mover_gigil_scriptado(trajeto[m["i"]]):
            m["i"] += 1
            if m["i"] >= len(trajeto):
                m["fase"] = "trabalhar"
                m["t"] = 0
    elif m["fase"] == "trabalhar":
        if m["t"] % 7 == 0:
            tela_ret = painel["tela"]
            criar_particulas(tela_ret.centerx, tela_ret.bottom, CIANO, 4, 1.6, 18, 2, 0.02)
        if m["t"] == 70:
            tocar("terminal")
        if m["t"] >= 110:
            concluir_painel(painel)
            m["fase"] = "sair"
            m["i"] = len(trajeto) - 2
    else:
        if mover_gigil_scriptado(trajeto[max(0, m["i"])]):
            m["i"] -= 1
            if m["i"] < 0:
                terminar_missao_gigil()



def desenhar_jogador(alvo):
    if jogador_piscar > 0 and (tempo // 4) % 2 == 0:
        return
    desenhar_sombra(alvo, jogador.centerx, jogador.bottom, 32, 10)
    if sprites_jogador is not None:
        quadros = sprites_jogador["quadros"][jogador_dir]
        if jogador_movendo:
            imagem = quadros[int(jogador_anim) % len(quadros)]
        else:
            imagem = sprites_jogador["parado"][jogador_dir]
        ax, ay = sprites_jogador["ancora"]
        alvo.blit(imagem, (jogador.centerx - ax, jogador.bottom + 2 - ay))
    else:
        alvo.blit(jogador_estatico, jogador_estatico.get_rect(
            midbottom=(jogador.centerx, jogador.bottom + 2)))



def imagem_da_gigil():
    """(imagem, âncora_x, âncora_y) da GIGIL (spritesheet ou foto)."""
    if sprites_gigil is not None:
        quadros = sprites_gigil["quadros"].get(gigil_dir) or sprites_gigil["quadros"]["baixo"]
        movendo = math.hypot(gigil_vel[0], gigil_vel[1]) > 0.6
        imagem = quadros[int(gigil_anim) % len(quadros)] if movendo else quadros[0]
        return imagem, sprites_gigil["ancora"][0], sprites_gigil["ancora"][1]
    imagem = gigil_img_direita if gigil_olhando >= 0 else gigil_img_esquerda
    return imagem, imagem.get_width() // 2, imagem.get_height()



def desenhar_gigil(alvo):
    movendo = math.hypot(gigil_vel[0], gigil_vel[1]) > 0.6
    salto = abs(math.sin(gigil_anim * 1.3)) * 3 if movendo else 0
    imagem, ax, ay = imagem_da_gigil()
    if gigil_no_duto:
        imagem = pygame.transform.smoothscale(
            imagem, (max(1, int(imagem.get_width() * 0.65)),
                     max(1, int(imagem.get_height() * 0.65))))
        ax, ay = imagem.get_width() // 2, imagem.get_height()
    desenhar_sombra(alvo, gigil.centerx, gigil.bottom, 34, 10, alpha=95)
    alvo.blit(imagem, (gigil.centerx - ax, int(gigil.bottom + 2 - salto - ay)))

    topo = gigil.bottom - ay - 6
    if gigil_estado == "presa":
        if distancia_pontos(jogador.center, gigil.center) < 260:
            texto = "Au! Au!" if (tempo // 40) % 2 == 0 else "Socorro!"
            desenhar_balao(alvo, gigil.centerx, topo, texto, AMARELO)
        elif cela_aberta:
            desenhar_balao(alvo, gigil.centerx, topo, "!", VERDE)
    elif gigil_estado == "seguindo" and gigil_sem_rota:
        desenhar_balao(alvo, gigil.centerx, topo, "?", CIANO)
    elif gigil_estado == "missao" and gigil_missao and gigil_missao["fase"] == "trabalhar":
        desenhar_balao(alvo, gigil.centerx, topo, "...", VERDE)



def desenhar_bloco_especial(alvo, bloco):
    tipo = bloco["tipo"]
    if tipo == "terminal":
        if "seg" in bloco:
            i = bloco["seg"]
            desenhar_terminal_bloco(alvo, bloco, i + 1, seg_ativos[i], 0, LARANJA, i)
        elif "interruptor" in bloco:
            ident = bloco["interruptor"]
            desenhar_terminal_bloco(
                alvo, bloco, "A" if ident == "s1" else "B",
                interruptores.get(ident, False), 0, AMARELO, 3)
        else:
            for i, t in enumerate(terminais):
                if t is bloco:
                    desenhar_terminal(alvo, i)
                    return
            desenhar_bloco(alvo, bloco)
    elif tipo == "console":
        desenhar_painel_central(alvo)
    elif tipo == "pedestal" and bloco.get("id"):
        desenhar_bloco(alvo, bloco)
        desenhar_registro(alvo, bloco)
    else:
        desenhar_bloco(alvo, bloco)



def desenhar_prompt_interacao(alvo):
    obj = interativo_proximo()
    if obj is None or estado != "jogando":
        return
    r = obj["rect"]
    altura = 40
    for bloco in blocos:
        if bloco["rect"] == r:
            altura = bloco["altura"] + 22
            break
    x = r.centerx
    y = r.y - altura + int(math.sin(tempo * 0.15) * 3)
    desenhar_balao(alvo, x, y, "E", AMARELO)



def formatar_tempo(segundos):
    segundos = max(0, int(segundos))
    return f"{segundos // 60}:{segundos % 60:02d}"



def desenhar_contador_hud():
    """Contadores no canto direito da barra de cima."""
    x = LARGURA - 12
    if fase_atual == 1:
        for i in range(3):
            icone = bateria_icone if i < baterias_coletadas else bateria_icone_apagada
            jogo.blit(icone, (x - 22 * (3 - i) - 4, 3))
        desenhar_texto(f"BATERIAS {baterias_coletadas}/3", x - 74, 6, AMARELO,
                       fonte_pequena, alvo=jogo, centro=False)
        return
    if fase_atual == 2:
        total = progresso_terminal
        rotulo = f"TERMINAIS {total}/3"
        lampadas = terminais_ativados
    elif fase_atual == 3:
        total = sum(seg_ativos)
        rotulo = f"TERMINAIS DE SEGURANÇA {total}/3 (faltam {3 - total})"
        lampadas = seg_ativos
    else:
        rotulo = f"SELAGEM {formatar_tempo(tempo_restante)}" if TEMPO_FASE_4 > 0 else "SETOR FINAL"
        lampadas = [rele_feito, interruptores.get("s1", False), interruptores.get("s2", False)]
    largura = fonte_pequena.size(rotulo)[0]
    cor = AMARELO
    if fase_atual == 4 and TEMPO_FASE_4 > 0 and tempo_restante < 60:
        cor = VERMELHO if (tempo // 15) % 2 == 0 else AMARELO
    desenhar_texto(rotulo, x - 3 * 20 - largura - 8, 6, cor, fonte_pequena, alvo=jogo)
    for i in range(3):
        cx = x - 50 + i * 20
        ligado = lampadas[i]
        pygame.draw.circle(jogo, VERDE if ligado else (60, 66, 90), (cx, 15), 7)
        pygame.draw.circle(jogo, BRANCO, (cx, 15), 7, 1)



def desenhar_inventario_hud():
    """Cartões e bateria que o jogador está carregando."""
    x = 14
    y = BARRA_TOPO + 6
    for cor_nome in ("azul", "vermelho"):
        if cor_nome in cartoes:
            cartao = pygame.Rect(x, y, 26, 18)
            pygame.draw.rect(jogo, CORES_CARTAO[cor_nome], cartao, border_radius=3)
            pygame.draw.rect(jogo, BRANCO, cartao, 1, border_radius=3)
            pygame.draw.rect(jogo, (240, 220, 120), (x + 4, y + 4, 7, 5))
            x += 32
    if tem_bateria:
        jogo.blit(bateria_icone, (x, y - 3))



def desenhar_seta_objetivo():
    texto, ponto = objetivo_atual()
    sx = ponto[0] - camera_x
    sy = ponto[1] - camera_y
    topo_util = BARRA_TOPO + 14
    base_util = BARRA_BASE - 14
    if 24 <= sx <= LARGURA - 24 and topo_util + 30 <= sy <= base_util:
        y = sy - 52 + math.sin(tempo * 0.12) * 5
        pygame.draw.polygon(jogo, (20, 30, 50),
                            [(sx - 10, y - 1), (sx + 10, y - 1), (sx, y + 16)])
        pygame.draw.polygon(jogo, CIANO, [(sx - 8, y), (sx + 8, y), (sx, y + 13)])
        return
    cx = jogador.centerx - camera_x
    cy = jogador.centery - camera_y - 30
    dx, dy = sx - cx, sy - cy
    if abs(dx) < 1 and abs(dy) < 1:
        return
    limites = [(40, LARGURA - 40), (topo_util + 26, base_util - 6)]
    t = 10 ** 6
    if dx > 0:
        t = min(t, (limites[0][1] - cx) / dx)
    elif dx < 0:
        t = min(t, (limites[0][0] - cx) / dx)
    if dy > 0:
        t = min(t, (limites[1][1] - cy) / dy)
    elif dy < 0:
        t = min(t, (limites[1][0] - cy) / dy)
    px, py = cx + dx * t, cy + dy * t
    norma = math.hypot(dx, dy)
    ux, uy = dx / norma, dy / norma
    ponta = (px + ux * 14, py + uy * 14)
    base1 = (px - ux * 8 - uy * 9, py - uy * 8 + ux * 9)
    base2 = (px - ux * 8 + uy * 9, py - uy * 8 - ux * 9)
    pygame.draw.polygon(jogo, (20, 30, 50), [ponta, base1, base2])
    pygame.draw.polygon(jogo, CIANO, [ponta, base1, base2], 2)



def desenhar_minimapa():
    """Mapa pequeno das fases grandes (3 e 4)."""
    if mundo_largura <= LARGURA and mundo_altura <= ALTURA:
        return
    escala = 150 / arena.width
    largura = 150
    altura = max(18, int(arena.height * escala))
    ret = pygame.Rect(LARGURA - largura - 10, BARRA_TOPO + 6, largura, altura)
    desenhar_painel(jogo, ret.inflate(6, 6), (8, 12, 22), 200, CINZA, 4, 1)

    def mapa(x, y):
        return (ret.x + (x - arena.x) * escala, ret.y + (y - arena.y) * escala)

    for r in obstaculos:
        px, py = mapa(r.x, r.y)
        pygame.draw.rect(jogo, (96, 108, 140),
                         (int(px), int(py), max(1, int(r.w * escala)), max(1, int(r.h * escala))))
    for porta in portas:
        if porta["prog"] < 0.85:
            r = porta["rect"]
            px, py = mapa(r.x, r.y)
            cor = CORES_CARTAO.get(porta.get("cor"), AMARELO)
            pygame.draw.rect(jogo, cor, (int(px), int(py), max(2, int(r.w * escala)), max(2, int(r.h * escala))))
    _, alvo_obj = objetivo_atual()
    if (tempo // 15) % 2 == 0:
        px, py = mapa(*alvo_obj)
        pygame.draw.circle(jogo, CIANO, (int(px), int(py)), 3)
    px, py = mapa(*gigil.center)
    pygame.draw.circle(jogo, AMARELO, (int(px), int(py)), 2)
    px, py = mapa(*jogador.center)
    pygame.draw.circle(jogo, BRANCO, (int(px), int(py)), 3)
    camera_ret = pygame.Rect(
        int(mapa(camera_x, camera_y + BARRA_TOPO)[0]), ret.y,
        max(4, int(LARGURA * escala)), altura
    ).clip(ret)
    pygame.draw.rect(jogo, (140, 160, 200), camera_ret, 1)



def criar_terminal_seg(rect, indice):
    """Terminal de segurança (fases 3): bloco + interação."""
    bloco = criar_bloco(rect, "terminal")
    bloco["seg"] = indice
    seg_blocos.append(bloco)
    interativos.append({
        "tipo": "terminal_seg", "rect": pygame.Rect(rect), "indice": indice
    })
    return bloco



def criar_porta_cartao(porta, cor):
    interativos.append({
        "tipo": "porta_cartao", "rect": porta["rect"], "porta": porta, "cor": cor
    })



def criar_plataformas(x0, y, quantidade, passo=56, lado=50, ciclo=240, ligado=150, atraso=45):
    return [
        {"rect": pygame.Rect(x0 + passo * i, y, lado, lado),
         "ciclo": ciclo, "ligado": ligado, "inicio": i * atraso}
        for i in range(quantidade)
    ]



def iniciar_fase4():
    global lasers, abismos, itens, sirenes, zonas_parede, saida
    global checkpoints, ponto_retorno, gigil_estado, gigil_segue
    global alarme_ativo, tempo_restante

    preparar_nivel_comum(4, 1940, 600, (20, 104, 1900, 432))

    # setor 1: labirinto curto e o interruptor A
    criar_bloco((580, 104, 40, 226), "parede")
    criar_bloco((580, 420, 40, 116), "parede")
    porta_d1 = criar_porta((580, 330, 40, 90), "trava", ident="d1")
    criar_bloco((200, 104, 46, 230), "servidor")
    criar_bloco((360, 300, 46, 236), "maquina")
    criar_bloco((90, 150, 56, 40), "caixa")
    criar_bloco((470, 112, 60, 30), "terminal")
    interativos.append({"tipo": "interruptor", "id": "s1",
                        "rect": pygame.Rect(470, 112, 60, 30), "porta": porta_d1})

    # setor 2: lasers, uma travessia de plataformas e o cartão vermelho
    criar_bloco((1240, 104, 40, 226), "parede")
    criar_bloco((1240, 420, 40, 116), "parede")
    porta_d2 = criar_porta((1240, 330, 40, 90), "trava", ident="d2", cor="vermelho")
    criar_porta_cartao(porta_d2, "vermelho")
    criar_bloco((880, 200, 56, 40), "caixa")
    criar_bloco((880, 110, 100, 34), "mesa")
    lasers = [
        {"rect": pygame.Rect(700, 104, 14, 432), "ciclo": 220, "ligado": 190, "inicio": 0},
        {"rect": pygame.Rect(1130, 104, 14, 432), "ciclo": 220, "ligado": 190, "inicio": 95},
        {"rect": pygame.Rect(1620, 104, 14, 432), "ciclo": 220, "ligado": 190, "inicio": 155},
    ]
    abismos = [{
        "rect": pygame.Rect(770, 456, 270, 80),
        "plataformas": criar_plataformas(774, 471, 5, passo=54),
    }]
    itens = [{"tipo": "cartao", "cor": "vermelho", "rect": pygame.Rect(1048, 468, 40, 40)}]

    # setor 3: relé no duto (GIGIL) + interruptor B abrem a saída
    criar_painel_gigil((1480, 104, 74, 64), "rele", "duto_rele")
    criar_bloco((1340, 290, 46, 246), "maquina")
    criar_bloco((1690, 112, 60, 30), "terminal")
    interativos.append({"tipo": "interruptor", "id": "s2",
                        "rect": pygame.Rect(1690, 112, 60, 30), "porta": None})
    criar_bloco((1780, 104, 46, 200), "servidor")
    criar_registro((1300, 120, 34, 26), "r5")

    saida = pygame.Rect(1862, 330, 58, 90)

    checkpoints = [
        (pygame.Rect(20, 104, 560, 432), (70, 500)),
        (pygame.Rect(620, 104, 80, 432), (660, 400)),
        (pygame.Rect(714, 104, 56, 350), (742, 400)),
        (pygame.Rect(714, 456, 56, 80), (742, 500)),
        (pygame.Rect(1040, 104, 90, 350), (1090, 400)),
        (pygame.Rect(1280, 104, 80, 432), (1320, 400)),
        (pygame.Rect(1540, 104, 80, 432), (1580, 400)),
    ]
    ponto_retorno = (70, 500)

    criar_cabo([(100, 520), (300, 520), (300, 400), (560, 400)])
    criar_cabo([(640, 300), (1220, 300)])
    criar_cabo([(1300, 400), (1850, 400), (1850, 380)])

    sirenes = [(160, 62), (480, 62), (800, 62), (1120, 62), (1440, 62), (1760, 62)]
    alarme_ativo = True
    tempo_restante = float(TEMPO_FASE_4)

    colocar_personagens(70, 500, 120, 500)
    gigil_estado = "seguindo"
    gigil_segue = True
    avisar("Corra! O setor será selado. Abra as portas e chegue à saída.")

    montar_cenario()
    atualizar_grade_se_preciso()
    atualizar_camera(True)



def centro_do_terminal(indice):
    if indice < len(terminais):
        return terminais[indice]["rect"].center
    painel = painel_gigil_da_fase()
    return painel["tela"].center if painel else jogador.center



def usar_terminal_seg(indice):
    global tem_bateria, energia_nivel
    if seg_ativos[indice]:
        return
    r = [b for b in seg_blocos if b.get("seg") == indice][0]["rect"]
    if indice == 2 and not tem_bateria:
        efeito_brilho(r.centerx, r.y - 20, VERMELHO, 10, 40)
        tocar("erro")
        avisar("Terminal sem energia! Precisa de uma bateria (a GIGIL pode buscar no duto).")
        return
    if indice == 2:
        tem_bateria = False
        avisar_curto = "Bateria instalada!"
        criar_texto_flutuante(avisar_curto, r.centerx, r.y - 60, AMARELO)
    seg_ativos[indice] = True
    energia_nivel = sum(seg_ativos) / 3
    efeito_brilho(r.centerx, r.y - 20, VERDE, 18, 64)
    criar_texto_flutuante("ATIVO!", r.centerx, r.y - 44, VERDE)
    tocar("terminal")
    faltam = 3 - sum(seg_ativos)
    if faltam == 0:
        desligar_seguranca()
    else:
        avisar(f"Terminal de segurança {indice + 1} ativado! Faltam {faltam}.")



def usar_porta_cartao(obj):
    cor = obj["cor"]
    porta = obj["porta"]
    centro = porta["rect"].center
    if cor in cartoes:
        abrir_porta(porta)
        efeito_brilho(centro[0], centro[1], CORES_CARTAO.get(cor, VERDE), 16, 60)
        mostrar_banner(f"CARTÃO {cor.upper()} ACEITO!", VERDE, 150)
        avisar(f"Cartão {cor} aceito! A porta se abriu.")
    else:
        tocar("erro")
        efeito_brilho(centro[0], centro[1], VERMELHO, 8, 36)
        avisar(f"Acesso negado: você precisa do cartão {cor}.")



def verificar_saida_fase4():
    global saida_aberta
    if rele_feito and interruptores.get("s2", False) and not saida_aberta:
        saida_aberta = True
        tocar("saida")
        tremer(3, 14)
        mostrar_banner("SAÍDA LIBERADA!", VERDE, 200)
        avisar("A saída externa abriu! Corra com a GIGIL!")
        efeito_brilho(saida.centerx, saida.centery, VERDE, 24, 80)



def voltar_ao_checkpoint(mensagem_aviso):
    global jogador_pos, jogador_piscar
    centro = jogador.center
    efeito_brilho(centro[0], centro[1] - 20, VERMELHO, 20)
    tocar("laser")
    tremer(5, 16)
    jogador.midbottom = ponto_retorno
    jogador_pos = [float(jogador.x), float(jogador.y)]
    jogador_piscar = 60
    avisar(mensagem_aviso)



def atualizar_perigos():
    """Choque dos lasers e queda nos buracos (só afetam o jogador)."""
    if jogador_piscar > 0:
        return
    for laser in lasers:
        if laser_ligado(laser) and jogador.colliderect(laser["rect"]):
            voltar_ao_checkpoint("Alerta! O laser te levou de volta ao último checkpoint.")
            return
    for abismo in abismos:
        if abismo["rect"].collidepoint(jogador.center):
            seguro = False
            for plat in abismo["plataformas"]:
                ativa, _ = plataforma_estado(plat)
                if ativa and plat["rect"].inflate(16, 16).collidepoint(jogador.center):
                    seguro = True
                    break
            if not seguro:
                voltar_ao_checkpoint("Você caiu! Espere as plataformas acenderem e tente de novo.")
                return



def coletar_itens():
    global tem_bateria
    for item in itens[:]:
        if jogador.colliderect(item["rect"].inflate(10, 10)):
            itens.remove(item)
            cor = item["cor"]
            cartoes.add(cor)
            r = item["rect"]
            efeito_brilho(r.centerx, r.centery - 16, CORES_CARTAO.get(cor, AMARELO), 18, 60)
            criar_texto_flutuante(f"CARTÃO {cor.upper()}", r.centerx, r.centery - 50,
                                  CORES_CARTAO.get(cor, AMARELO))
            tocar("coleta")
            avisar(f"Você pegou o cartão {cor}! Ele abre uma porta trancada.")



def selar_setor():
    """O tempo acabou: o setor é selado e a fase recomeça."""
    iniciar_fase4()
    mostrar_banner("O SETOR FOI SELADO!", VERMELHO, 200)
    avisar("O tempo acabou e o setor foi selado. Tente de novo, mais rápido!")
    tremer(5, 20)



def atualizar_fase4():
    global ponto_retorno, tempo_restante

    coletar_itens()
    for zona, ponto in checkpoints:
        if zona.collidepoint(jogador.center):
            ponto_retorno = ponto
    atualizar_perigos()

    if TEMPO_FASE_4 > 0 and not saida_aberta:
        tempo_restante -= 1.0 / FPS
        if tempo_restante <= 0:
            selar_setor()
            return

    if jogador.colliderect(saida):
        if not saida_aberta:
            avisar_com_pausa("saida", "A saída ainda está trancada: falta o relé ou o interruptor B.")
        elif not gigil_perto_do_jogador():
            avisar_com_pausa("saida", "Espere a GIGIL chegar até você!", 90)
        else:
            concluir_fase()



def porta_por_id(ident):
    for porta in portas:
        if porta.get("id") == ident:
            return porta
    return None



if __name__ == "__main__":
    executar()

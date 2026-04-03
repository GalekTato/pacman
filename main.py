"""
main.py  –  Pac-Man con Poda Alfa-Beta
Corregido: posiciones reales en el laberinto, HUD ligero, camara ajustada.
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math, os, sys, numpy as np, pandas as pd

sys.path.append('.')
from Pacman import Pacman
from Ghost  import Ghost

# ──────────────────────────────────────────────────
#  PANTALLA
# ──────────────────────────────────────────────────
W, H = 1000, 800
FOVY, ZNEAR, ZFAR = 60.0, 0.01, 1200.0

DimBoard = 400
CENTER_X, CENTER_Y, CENTER_Z = 200.0, 0.0, 200.0
EYE_Y = 380.0
theta  = 0.0
radius = 480.0

textures = []

BASE  = os.path.abspath(os.path.dirname(__file__))
f_map     = os.path.join(BASE, 'mapa.bmp')
f_pacman  = os.path.join(BASE, 'pacman.bmp')
f_ghost   = [os.path.join(BASE, f'fantasma{i}.bmp') for i in range(1,5)]
f_csv     = os.path.join(BASE, 'mapa.csv')

matrix = np.array(pd.read_csv(f_csv, header=None)).astype("int")

# ──────────────────────────────────────────────────
#  MATRIZ DE CONTROL  (10×10)
# ──────────────────────────────────────────────────
MC = [
    [10, 0,21, 0,11,10, 0,21, 0,11],
    [24, 0,25,21,23,23,21,25, 0,22],
    [12, 0,22,12,11,10,13,24, 0,13],
    [ 0, 0, 0,10,23,23,11, 0, 0, 0],
    [26, 0,25,22, 0, 0,24,25, 0,27],
    [ 0, 0, 0,24, 0, 0,22, 0, 0, 0],
    [10, 0,25,23,11,10,23,25, 0,11],
    [12,11,24,21,23,23,21,22,10,13],
    [10,23,13,12,11,10,13,12,23,11],
    [12, 0, 0, 0,23,23, 0, 0, 0,13],
]

XPxToMC = np.full(359, -1, dtype=int)
for idx, v in zip([0,30,71,114,156,199,242,286,328,358], range(10)):
    XPxToMC[idx] = v

YPxToMC = np.full(361, -1, dtype=int)
for idx, v in zip([0,51,90,130,168,208,244,282,320,360], range(10)):
    YPxToMC[idx] = v

# ──────────────────────────────────────────────────
#  POSICIONES DE INICIO  (offset +20, sobre intersecciones reales)
#  pixel(col, row) → position_x = col+20, position_z = row+20
#
#  Pacman      → MC(0,0)  pixel(0,0)    → pos(20,20)    dir→derecha
#  Blinky(0)   → MC(9,9)  pixel(358,360)→ pos(378,380)  dir→arriba
#  Pinky (1)   → MC(9,0)  pixel(358,0)  → pos(378,20)   dir→abajo
#  Inky  (2)   → MC(0,9)  pixel(0,360)  → pos(20,380)   dir→arriba
#  Clyde (3)   → MC(0,7)  pixel(0,282)  → pos(20,302)   dir→derecha
# ──────────────────────────────────────────────────
pc = Pacman(matrix, MC, XPxToMC, YPxToMC)

ghosts = [
    Ghost(matrix, MC, XPxToMC, YPxToMC, 378, 380, 0, 0),   # Blinky  rojo
    Ghost(matrix, MC, XPxToMC, YPxToMC, 378,  20, 2, 1),   # Pinky   rosa
    Ghost(matrix, MC, XPxToMC, YPxToMC,  20, 380, 0, 2),   # Inky    cian
    Ghost(matrix, MC, XPxToMC, YPxToMC,  20, 302, 1, 3),   # Clyde   naranja
]
ghosts[2].set_partner(ghosts[3])
ghosts[3].set_partner(ghosts[2])

# ──────────────────────────────────────────────────
#  ESTADO
# ──────────────────────────────────────────────────
paused    = False
show_info = True
flash     = 0          # frames de flash al colision
frame     = 0

NAMES = {0:"Blinky (aleatorio)", 1:"Pinky (alfa-beta)",
         2:"Inky (colaborativo)", 3:"Clyde (colaborativo)"}

# ──────────────────────────────────────────────────
#  OPENGL / PYGAME
# ──────────────────────────────────────────────────
pygame.init()
font = pygame.font.SysFont("Consolas", 15, bold=True)

def load_tex(path):
    textures.append(glGenTextures(1))
    idx = len(textures) - 1
    glBindTexture(GL_TEXTURE_2D, textures[idx])
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    img  = pygame.image.load(path).convert()
    w, h = img.get_rect().size
    data = pygame.image.tostring(img, "RGBA")
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    glGenerateMipmap(GL_TEXTURE_2D)

def init():
    pygame.display.set_mode((W, H), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Pac-Man  –  Poda Alfa-Beta")

    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(FOVY, W/H, ZNEAR, ZFAR)
    glMatrixMode(GL_MODELVIEW);  glLoadIdentity()
    _lookat()
    glClearColor(0.04, 0.04, 0.08, 1)
    glEnable(GL_DEPTH_TEST)

    load_tex(f_map)          # 0
    load_tex(f_pacman)       # 1
    for f in f_ghost:        # 2..5
        load_tex(f)

    pc.loadTextures(textures, 1)
    for i, g in enumerate(ghosts):
        g.loadTextures(textures, i + 2)

def _lookat():
    ex = radius*(math.cos(math.radians(theta)) + math.sin(math.radians(theta))) + CENTER_X
    ez = radius*(-math.sin(math.radians(theta)) + math.cos(math.radians(theta))) + CENTER_Z
    glLoadIdentity()
    gluLookAt(ex, EYE_Y, ez, CENTER_X, CENTER_Y, CENTER_Z, 0, 1, 0)

# ──────────────────────────────────────────────────
#  HUD  (pygame 2D sobre OpenGL, sin glDrawPixels)
#  Se usa un pygame.Surface temporal y se dibuja
#  como textura OpenGL  → rápido en Windows
# ──────────────────────────────────────────────────
_hud_tex_id = None

def _init_hud_texture():
    global _hud_tex_id
    _hud_tex_id = int(glGenTextures(1))
    glBindTexture(GL_TEXTURE_2D, _hud_tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

_hud_surf = None   # reutilizar para no re-allocar cada frame

def render_hud(fps):
    global _hud_surf
    if _hud_tex_id is None:
        return

    # Dibujar texto sobre surface pygame
    if _hud_surf is None:
        _hud_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    _hud_surf.fill((0, 0, 0, 0))

    y = 6
    def line(txt, col=(200, 220, 255)):
        nonlocal y
        s = font.render(txt, True, col)
        _hud_surf.blit(s, (8, y))
        y += 17

    line(f"FPS {fps:.0f}  |  WASD = Pacman   ←→ = camara   P = pausa   I = info   ESC = salir",
         (180, 180, 255))

    if show_info:
        line("─" * 52, (80, 80, 120))
        line("Blinky  (rojo)   ▸ movimiento ALEATORIO",         (255, 100, 100))
        line("Pinky   (rosa)   ▸ ALFA-BETA individual",          (255, 160, 220))
        line("Inky    (cian)   ▸ ALFA-BETA colaborativo (pinza)",(100, 230, 230))
        line("Clyde   (naranja)▸ ALFA-BETA colaborativo (pinza)",(255, 160,  60))
        line("─" * 52, (80, 80, 120))
        line("Mejoras: Tabu horizonte 8  |  Greedy ordering  |  Quiescence +1", (160,200,160))

    if paused:
        s = font.render("  PAUSADO  (P para continuar)  ", True, (20, 20, 20),
                        (240, 220, 60))
        _hud_surf.blit(s, (W//2 - s.get_width()//2, H//2 - 12))

    if flash > 0:
        s = font.render("  PACMAN ATRAPADO!  ", True, (255, 255, 255), (180, 20, 20))
        _hud_surf.blit(s, (W//2 - s.get_width()//2, H//2 + 20))

    # Subir como textura OpenGL (flip vertical para OpenGL)
    data = pygame.image.tostring(_hud_surf, "RGBA", True)
    glBindTexture(GL_TEXTURE_2D, _hud_tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, W, H, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)

def blit_hud():
    if _hud_tex_id is None:
        return
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    glOrtho(0, W, 0, H, -1, 1)
    glMatrixMode(GL_MODELVIEW);  glPushMatrix(); glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND);  glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, _hud_tex_id)
    glColor4f(1, 1, 1, 1)
    glBegin(GL_QUADS)
    glTexCoord2f(0,0); glVertex2f(0, 0)
    glTexCoord2f(1,0); glVertex2f(W, 0)
    glTexCoord2f(1,1); glVertex2f(W, H)
    glTexCoord2f(0,1); glVertex2f(0, H)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)

    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()

# ──────────────────────────────────────────────────
#  COLISION
# ──────────────────────────────────────────────────
def check_collision():
    THR = 14
    for g in ghosts:
        if (abs(g.position[0] - pc.position[0]) < THR and
            abs(g.position[2] - pc.position[2]) < THR):
            return True
    return False

def get_partner_mc(g):
    if g.partner is None:
        return None
    qx = g.partner.XPxToMC[max(0, g.partner.position[0]-20)]
    qy = g.partner.YPxToMC[max(0, g.partner.position[2]-20)]
    return (qx, qy) if qx != -1 and qy != -1 else None

# ──────────────────────────────────────────────────
#  RENDER ESCENA
# ──────────────────────────────────────────────────
def draw_scene():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # Mapa
    glColor3f(1, 1, 1)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textures[0])
    glBegin(GL_QUADS)
    glTexCoord2f(0,0); glVertex3d(0,0,0)
    glTexCoord2f(0,1); glVertex3d(0,0,DimBoard)
    glTexCoord2f(1,1); glVertex3d(DimBoard,0,DimBoard)
    glTexCoord2f(1,0); glVertex3d(DimBoard,0,0)
    glEnd()
    glDisable(GL_TEXTURE_2D)

    pc.draw()
    for g in ghosts:
        g.draw()

# ──────────────────────────────────────────────────
#  LOOP
# ──────────────────────────────────────────────────
init()
_init_hud_texture()
clock = pygame.time.Clock()
done  = False

while not done:
    for ev in pygame.event.get():
        if ev.type == QUIT:
            done = True
        if ev.type == KEYDOWN:
            if ev.key == K_ESCAPE: done   = True
            if ev.key == K_p:      paused = not paused
            if ev.key == K_i:      show_info = not show_info

    keys = pygame.key.get_pressed()

    if keys[K_RIGHT]: theta = (theta + 1.0) % 360; _lookat()
    if keys[K_LEFT]:  theta = (theta - 1.0) % 360; _lookat()

    if not paused:
        # Pacman
        if   keys[K_w]: pc.update(0)
        elif keys[K_d]: pc.update(1)
        elif keys[K_s]: pc.update(2)
        elif keys[K_a]: pc.update(3)
        else:           pc.update(-1)

        # Fantasmas cada 2 frames (velocidad razonable)
        if frame % 2 == 0:
            for g in ghosts:
                pm = get_partner_mc(g) if g.tipo in (2, 3) else None
                g.update2(pc.position, partner_mc=pm)

        if check_collision():
            flash = 45
        if flash > 0:
            flash -= 1

    draw_scene()
    render_hud(clock.get_fps())
    blit_hud()

    pygame.display.flip()
    clock.tick(60)
    frame += 1

pygame.quit()
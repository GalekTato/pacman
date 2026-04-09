"""
Ghost.py  –  4 fantasmas para Pac-Man con Poda Alfa-Beta
==========================================================
Blinky  (tipo 0) – rojo    – movimiento aleatorio
Pinky   (tipo 1) – rosa    – alfa-beta individual
Inky    (tipo 2) – cian    – alfa-beta colaborativo
Clyde   (tipo 3) – naranja – alfa-beta colaborativo
"""

import math
import random
from OpenGL.GL import *

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

_OPTIONS = {
    10: [1, 2],   11: [2, 3],   12: [0, 1],   13: [0, 3],
    21: [1, 2, 3], 22: [0, 2, 3], 23: [0, 1, 3], 24: [0, 1, 2],
    25: [0, 1, 2, 3], 26: [1], 27: [3],
}
_INV   = {0: 2, 1: 3, 2: 0, 3: 1}
_DELTA = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}

class Ghost:
    def __init__(self, mapa, mc, x_mc, y_mc, xini, yini, direction, tipo):
        self.MC       = mc
        self.XPxToMC  = x_mc
        self.YPxToMC  = y_mc
        self.mapa     = mapa
        self.position = [xini, 1, yini]
        self.positionMC = [
            self.XPxToMC[self.position[0] - 20],
            self.YPxToMC[self.position[2] - 20],
        ]
        self.direction = direction
        self.tipo      = tipo

        _COLORS = {0: (1.0, 0.15, 0.15), 1: (1.0, 0.5, 0.85),
                   2: (0.1, 0.9,  0.9),  3: (1.0, 0.6, 0.1)}
        self.color = _COLORS.get(tipo, (1.0, 1.0, 1.0))

        # Doble buffer de posicion para interpolacion suave
        self.render_pos = [float(xini), 1.0, float(yini)]
        self._prev_pos  = [float(xini), 1.0, float(yini)]
        self._lerp_t    = 1.0

        # Tabu global con horizonte limitado
        self._tabu      = []
        self._TABU_SIZE = 8

        self.partner   = None
        self.texturas  = None
        self.Id        = 0

    def set_partner(self, other):
        self.partner = other

    def loadTextures(self, texturas, id):
        self.texturas = texturas
        self.Id = id

    # ------------------------------------------------------------------ movimiento base
    def _apply_dir(self, d):
        self._prev_pos = list(self.position)
        dx, dz = _DELTA[d]
        nx = self.position[0] + dx
        nz = self.position[2] + dz
        
        # Validación estricta para no salir del arreglo
        if 0 <= nx - 20 < len(self.XPxToMC) and 0 <= nz - 20 < len(self.YPxToMC):
            self.position[0] = nx
            self.position[2] = nz
            self.direction = d
        self._lerp_t = 0.0

    def _continue(self):
        self._prev_pos = list(self.position)
        dx, dz = _DELTA[self.direction]
        nx = self.position[0] + dx
        nz = self.position[2] + dz
        
        # Validación estricta para no salir del arreglo
        if 0 <= nx - 20 < len(self.XPxToMC) and 0 <= nz - 20 < len(self.YPxToMC):
            self.position[0] = nx
            self.position[2] = nz
        self._lerp_t = 0.0

    def _cell_options(self):
        px = self.position[0] - 20
        pz = self.position[2] - 20
        if not (0 <= px < len(self.XPxToMC) and 0 <= pz < len(self.YPxToMC)):
            return None, []
        cx = self.XPxToMC[px];  cy = self.YPxToMC[pz]
        if cx == -1 or cy == -1:
            return None, []
        self.positionMC[0] = cx;  self.positionMC[1] = cy
        celId = self.MC[cy][cx]
        if celId == 0:
            return 0, []
        opts = list(_OPTIONS.get(celId, []))
        d_inv = _INV[self.direction]
        if d_inv in opts and len(opts) > 1:
            opts.remove(d_inv)
        return celId, opts

    # ------------------------------------------------------------------ Blinky aleatorio
    def _move_random(self):
        celId, opts = self._cell_options()
        if celId is None or celId == 0 or not opts:
            self._continue(); return
        self._apply_dir(random.choice(opts))

# ------------------------------------------------------------------ funciones eval
    def _eval_pinky(self, ghost_mc, _partner_mc, pacman_mc):
        dist = manhattan(ghost_mc, pacman_mc)
        c1   = 1.0 - min(dist / 13.0, 1.0)
        c2   = 0.25 if (ghost_mc[0] == pacman_mc[0] or
                        ghost_mc[1] == pacman_mc[1]) else 0.0
                        
        # MEJORA (Ruptura de simetría): Ruido minúsculo para evitar rutas idénticas
        c3   = random.uniform(0.0, 0.02)
        return c1 + c2 + c3

    def _eval_collab(self, ghost_mc, partner_mc, pacman_mc):
        dist = manhattan(ghost_mc, pacman_mc)
        c1   = 1.0 - min(dist / 13.0, 1.0)
        
        if partner_mc is not None:
            gx, gy = ghost_mc;  px, py = pacman_mc;  qx, qy = partner_mc
            v1 = (px - gx, py - gy);  v2 = (px - qx, py - qy)
            m1 = math.sqrt(v1[0]**2 + v1[1]**2) + 1e-9
            m2 = math.sqrt(v2[0]**2 + v2[1]**2) + 1e-9
            cos_a = (v1[0]*v2[0] + v1[1]*v2[1]) / (m1 * m2)
            c2 = 0.35 * (-cos_a)
            
            dist_partner = manhattan(ghost_mc, partner_mc)
            # MEJORA (Anti-Traslape): Castigo drástico si intentan fusionarse en la misma celda
            if dist_partner == 0:
                c3 = -5.0 
            else:
                c3 = 0.15 * min(dist_partner / 6.0, 1.0)
        else:
            c2 = c3 = 0.0
            
        # MEJORA (Ruptura de simetría): Evita que Inky y Clyde piensen exactamente igual
        c4 = random.uniform(0.0, 0.02)
        return c1 + c2 + c3 + c4

    # ------------------------------------------------------------------ alfa-beta
    def _get_dirs_mc(self, mc_pos, came_from):
        cx, cy = mc_pos
        if not (0 <= cx < len(self.MC[0]) and 0 <= cy < len(self.MC)):
            return []
        celId = self.MC[cy][cx]
        opts  = list(_OPTIONS.get(celId, []))
        if came_from != -1 and len(opts) > 1 and came_from in opts:
            opts.remove(came_from)
        return opts

    def _sim(self, pos, d):
        dx, dz = _DELTA[d]
        return (pos[0] + dx, pos[1] + dz)

    def alfa_beta(self, depth, alpha, beta, maximizing,
                  ghost_mc, pacman_mc, partner_mc,
                  came_from, branch_visited, eval_fn,
                  quiescence_used=False):
        if ghost_mc in branch_visited:
            return eval_fn(ghost_mc, partner_mc, pacman_mc)

        dist = manhattan(ghost_mc, pacman_mc)
        if depth <= 0:
            if dist <= 3 and not quiescence_used:
                depth = 1;  quiescence_used = True
            else:
                return eval_fn(ghost_mc, partner_mc, pacman_mc)

        dirs = self._get_dirs_mc(ghost_mc, came_from)
        if not dirs:
            return eval_fn(ghost_mc, partner_mc, pacman_mc)

        dirs.sort(key=lambda d: -eval_fn(self._sim(ghost_mc, d), partner_mc, pacman_mc))
        new_vis = branch_visited | {ghost_mc}

        if maximizing:
            val = -math.inf
            for d in dirs:
                child = self._sim(ghost_mc, d)
                if not (0 <= child[0] < len(self.MC[0]) and 0 <= child[1] < len(self.MC)):
                    continue
                v = self.alfa_beta(depth-1, alpha, beta, False,
                                   child, pacman_mc, partner_mc,
                                   _INV[d], new_vis, eval_fn, quiescence_used)
                val = max(val, v);  alpha = max(alpha, val)
                if beta <= alpha: break
            return val
        else:
            val = math.inf
            for d in dirs:
                child = self._sim(ghost_mc, d)
                if not (0 <= child[0] < len(self.MC[0]) and 0 <= child[1] < len(self.MC)):
                    continue
                v = self.alfa_beta(depth-1, alpha, beta, True,
                                   child, pacman_mc, partner_mc,
                                   _INV[d], new_vis, eval_fn, quiescence_used)
                val = min(val, v);  beta = min(beta, val)
                if beta <= alpha: break
            return val

    def _best_dir_ab(self, depth, pacman_mc, partner_mc, eval_fn):
        ghost_mc = tuple(self.positionMC)
        inv_cur  = _INV.get(self.direction, -1)
        dirs     = self._get_dirs_mc(ghost_mc, inv_cur)
        if not dirs:
            return self.direction

        dirs.sort(key=lambda d: -eval_fn(self._sim(ghost_mc, d), partner_mc, pacman_mc))
        best_val = -math.inf;  best_d = dirs[0]
        root_vis = frozenset([ghost_mc])

        for d in dirs:
            child = self._sim(ghost_mc, d)
            if not (0 <= child[0] < len(self.MC[0]) and 0 <= child[1] < len(self.MC)):
                continue
            v = self.alfa_beta(depth-1, -math.inf, math.inf, False,
                               child, pacman_mc, partner_mc,
                               _INV[d], root_vis | frozenset([child]),
                               eval_fn, quiescence_used=False)
            if v > best_val:
                best_val = v;  best_d = d

        self._tabu.append(ghost_mc)
        if len(self._tabu) > self._TABU_SIZE:
            self._tabu.pop(0)
        return best_d

    # ------------------------------------------------------------------ movimientos IA
    def _move_pinky(self, pacman_mc):
        celId, opts = self._cell_options()
        if celId is None or celId == 0 or not opts:
            self._continue(); return
        self._apply_dir(self._best_dir_ab(3, pacman_mc, None, self._eval_pinky))

    def _move_collab(self, pacman_mc, partner_mc_coords):
        celId, opts = self._cell_options()
        if celId is None or celId == 0 or not opts:
            self._continue(); return
        self._apply_dir(self._best_dir_ab(3, pacman_mc, partner_mc_coords, self._eval_collab))

    # ------------------------------------------------------------------ update principal
    def update2(self, pacmanXY, partner_mc=None):
        px = pacmanXY[0] - 20;  pz = pacmanXY[2] - 20
        pac_cx = self.XPxToMC[px] if 0 <= px < len(self.XPxToMC) else -1
        pac_cy = self.YPxToMC[pz] if 0 <= pz < len(self.YPxToMC) else -1
        pacman_mc = (pac_cx, pac_cy)

        gx = self.position[0] - 20;  gz = self.position[2] - 20
        in_inter = (0 <= gx < len(self.XPxToMC) and 0 <= gz < len(self.YPxToMC) and
                    self.XPxToMC[gx] != -1 and self.YPxToMC[gz] != -1)

        if in_inter:
            if   self.tipo == 0: self._move_random()
            elif self.tipo == 1: self._move_pinky(pacman_mc)
            else:                self._move_collab(pacman_mc, partner_mc)
        else:
            self._continue()

        self._lerp_t = min(self._lerp_t + 0.3, 1.0)
        for i in (0, 2):
            self.render_pos[i] = (self._prev_pos[i] * (1.0 - self._lerp_t) +
                                  self.position[i] * self._lerp_t)

    # ------------------------------------------------------------------ render
    def draw(self):
        glPushMatrix()
        glColor3f(*self.color)
        glTranslatef(self.render_pos[0], self.render_pos[1], self.render_pos[2])
        glScaled(10, 1, 10)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texturas[self.Id])
        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex3f(-1,1,-1)
        glTexCoord2f(0,1); glVertex3f(-1,1, 1)
        glTexCoord2f(1,1); glVertex3f( 1,1, 1)
        glTexCoord2f(1,0); glVertex3f( 1,1,-1)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()
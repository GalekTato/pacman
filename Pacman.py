"""
Pacman.py  –  Pacman con interpolacion suave de movimiento.
"""
from OpenGL.GL import *

class Pacman:
    def __init__(self, mapa, mc, x_mc, y_mc):
        self.MC       = mc
        self.XPxToMC  = x_mc
        self.YPxToMC  = y_mc
        self.mapa     = mapa
        self.position = [20, 1, 20]        # MC(0,0) pixel(0,0)
        self.positionMC = [
            self.XPxToMC[self.position[0] - 20],
            self.YPxToMC[self.position[2] - 20],
        ]
        self.direction = 1   # derecha
        self.start     = 1

        # Doble buffer de posicion
        self.render_pos = [20.0, 1.0, 20.0]
        self._prev_pos  = [20.0, 1.0, 20.0]
        self._lerp_t    = 1.0

    def loadTextures(self, texturas, id):
        self.texturas = texturas
        self.Id = id

    def update(self, dir):
        self._prev_pos = [float(self.position[0]), 1.0, float(self.position[2])]
        moved = False

        in_inter = (self.YPxToMC[self.position[2]-20] != -1 and
                    self.XPxToMC[self.position[0]-20] != -1)

        if in_inter:
            self.positionMC[0] = self.XPxToMC[self.position[0]-20]
            self.positionMC[1] = self.YPxToMC[self.position[2]-20]
            cell = self.MC[self.positionMC[1]][self.positionMC[0]]

            if cell == 0:          # falsa interseccion: sigue recto
                if self.direction == 0: self.position[2] -= 1
                elif self.direction==1: self.position[0] += 1
                elif self.direction==2: self.position[2] += 1
                else:               self.position[0] -= 1
                moved = True
            else:
                if dir == -1 and self.start != 1:
                    dir = self.direction

                can = {
                    0: cell in (12,13,22,23,24,25),
                    1: cell in (10,12,21,23,24,25,26),
                    2: cell in (10,11,21,22,24,25),
                    3: cell in (11,13,21,22,23,25,27),
                }
                if dir in can and can[dir]:
                    self.direction = dir
                    if dir==0: self.position[2] -= 1
                    elif dir==1: self.position[0] += 1
                    elif dir==2: self.position[2] += 1
                    else:        self.position[0] -= 1
                    self.start = 0
                    moved = True
        else:
            inv = {0:2,1:3,2:0,3:1}
            if dir == inv.get(self.direction, -1):
                self.direction = dir
            if self.direction==0: self.position[2] -= 1
            elif self.direction==1: self.position[0] += 1
            elif self.direction==2: self.position[2] += 1
            else:                   self.position[0] -= 1
            moved = True

        if moved:
            self._lerp_t = 0.0
        self._lerp_t = min(self._lerp_t + 0.3, 1.0)
        for i in (0, 2):
            self.render_pos[i] = (self._prev_pos[i]*(1-self._lerp_t) +
                                  self.position[i]*self._lerp_t)

    def draw(self):
        glPushMatrix()
        glColor3f(1.0, 1.0, 0.0)
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
import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    x_diff, y_diff = dst.centerx - org.centerx, dst.centery - org.centery
    norm = math.sqrt(x_diff**2 + y_diff**2)
    # normが0に近い場合を保護
    if norm == 0:
        return 0.0, 0.0
    return x_diff / norm, y_diff / norm


class Bird(pg.sprite.Sprite):
    delta = {
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)
        self.imgs = {
            (+1, 0): img,
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),
            (-1, 0): img0,
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10

    def change_img(self, num: int, screen: pg.Surface):
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed * sum_mv[0], self.speed * sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed * sum_mv[0], -self.speed * sum_mv[1])
        if sum_mv != [0, 0]:
            # 正規化された方向タプルにする（-1,0,1 の組み合わせ）
            dx = 1 if sum_mv[0] > 0 else (-1 if sum_mv[0] < 0 else 0)
            dy = 1 if sum_mv[1] > 0 else (-1 if sum_mv[1] < 0 else 0)
            self.dire = (dx, dy)
            # imgs に存在するキーであれば更新
            if self.dire in self.imgs:
                self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255),
              (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        super().__init__()
        rad = random.randint(10, 50)
        self.image = pg.Surface((2 * rad, 2 * rad))
        color = random.choice(__class__.colors)
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()

        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery + emy.rect.height // 2
        self.speed = 6

        self.inactive = False  # EMP 無効化状態

    def update(self):
        # inactive の場合は速度を半減して移動（仕様通り）
        if self.inactive:
            self.rect.move_ip((self.speed / 2) * self.vx, (self.speed / 2) * self.vy)
        else:
            self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)

        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    def __init__(self, bird: Bird):
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx
        self.speed = 10

    def update(self):
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    def __init__(self, obj: "Bomb|Enemy", life: int):
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        self.life -= 1
        self.image = self.imgs[self.life // 10 % 2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT // 2)
        self.state = "down"
        self.interval = random.randint(50, 300)

        self.disabled = False  # EMP で無効化される

    def update(self):
        # disabled のときは停止処理（爆弾投下も interval を inf にしているのでここでは移動の制御のみ）
        if not self.disabled:
            if self.rect.centery > self.bound:
                self.vy = 0
                self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)
    
    


class Score:
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT - 50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class EMP:
    """EMP（電磁パルス）機能"""
    def __init__(self, emys: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        # --- 敵機の無力化 ---
        for emy in emys:
            emy.disabled = True
            emy.interval = float("inf")  # 爆弾を落とさなくする

            # --- ラプラシアン風フィルタ（NumPyなし） ---
            try:
                # Pygameの surfarray laplacian がある環境ではそちらを使用
                emy.image = pg.transform.laplacian(emy.image)
            except Exception:
                # 無い場合は疑似ラプラシアンを適用
                emy.image = self.fake_laplacian(emy.image)

            # rect を保つ
            emy.rect = emy.image.get_rect(center=emy.rect.center)

        # --- 爆弾の無力化 ---
        for bomb in bombs:
            bomb.inactive = True
            bomb.speed = max(1, bomb.speed / 2)

        # --- EMPフラッシュ ---
        surf = pg.Surface((WIDTH, HEIGHT))
        surf.set_alpha(120)
        surf.fill((255, 255, 0))
        screen.blit(surf, (0, 0))
        pg.display.update()
        time.sleep(0.05)

    def fake_laplacian(self, surf: pg.Surface) -> pg.Surface:
        w, h = surf.get_size()
        base = surf.copy()

        offset1 = pg.Surface((w, h), pg.SRCALPHA)
        offset2 = pg.Surface((w, h), pg.SRCALPHA)

        offset1.blit(surf, (-1, 0))   # 左へ
        offset2.blit(surf, (1, 0))    # 右へ

        base.blit(offset1, (0, 0), special_flags=pg.BLEND_RGB_SUB)
        base.blit(offset2, (0, 0), special_flags=pg.BLEND_RGB_SUB)

        # うっすら白を追加して「無力化」感を出す
        white = pg.Surface((w, h))
        white.fill((120, 120, 120))
        base.blit(white, (0, 0), special_flags=pg.BLEND_RGB_ADD)

        return base





def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()

    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    beams.add(Beam(bird))
                if event.key == pg.K_e and score.value >= 20:
                    # EMP 発動
                    score.value -= 20
                    EMP(emys, bombs, screen)

        screen.blit(bg_img, [0, 0])

        if tmr % 200 == 0:
            emys.add(Enemy())

        # 敵機が停止状態で interval に応じて爆弾投下。ただし disabled (EMP) の敵は投下しない
        for emy in emys:
            if emy.state == "stop" and not emy.disabled and tmr % emy.interval == 0:
                bombs.add(Bomb(emy, bird))

        # 敵機とビームの衝突（倒された敵は消える）
        # groupcollide の戻りは {emy: [list of beams hit it]}
        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))
            score.value += 10
            bird.change_img(6, screen)

        # ビームと爆弾の当たり判定
        # bombs と beams を自動killさせずに衝突結果を取得して
        # inactive フラグを見て処理する（inactive は爆発させない）
        collisions = pg.sprite.groupcollide(bombs, beams, False, True)  # bombs は自動削除しない
        for bomb, hit_beams in collisions.items():
            if getattr(bomb, "inactive", False):
                # EMP無効化された爆弾は当たっても爆発せずに消えるだけ
                bomb.kill()
                continue
            # 通常爆弾は爆発させて kill
            exps.add(Explosion(bomb, 50))
            score.value += 1
            bomb.kill()

        # こうかとんと爆弾の衝突処理
        bird_hits = pg.sprite.spritecollide(bird, bombs, False)  # 自動killしない
        for bomb in bird_hits:
            if getattr(bomb, "inactive", False):
                # EMPで無効化された爆弾は爆発せずに消えるだけ（ダメージなし）
                bomb.kill()
                continue
            # 通常爆弾に当たった → ゲームオーバーの処理（元の挙動を維持）
            bird.change_img(8, screen)
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        # 更新・描画
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
import tkinter as tk
from tkinter import simpledialog, filedialog, colorchooser, messagebox
import json
import time

class TacticalBoard:
    # 定数の定義
    WIDTH, HEIGHT = 850, 650
    PITCH_COLOR = "#2e8b57"
    FOOTER_COLOR = "#1e5c3a"
    TEMP_FILE = "temp_save.json"

    def __init__(self, root):
        self.root = root
        self.root.title("Football Tactics Board - Professional Formations")
        self.root.resizable(False, False)
        
        self.current_file_path = None # 現在開いているファイルのパスを保持

        # --- メインメニュー ---
        menu_frame = tk.Frame(root)
        menu_frame.pack(fill=tk.X)
        
        # ホームチーム操作 (4231, 532, 3421を追加)
        tk.Label(menu_frame, text="[HOME]", fg="black", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)
        for fmt in ["4-3-3", "4-4-2", "3-5-2", "4-2-3-1", "5-3-2", "3-4-2-1"]:
            tk.Button(menu_frame, text=fmt, command=lambda f=fmt: self.change_team_formation("home", f)).pack(side=tk.LEFT)
        tk.Button(menu_frame, text="+控え", command=lambda: self.add_substitutes("home"), bg="#f0f0f0").pack(side=tk.LEFT, padx=(2, 10))
        
        # アウェイチーム操作 (4231, 532, 3421を追加)
        tk.Label(menu_frame, text=" [AWAY]", fg="blue", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)
        for fmt in ["4-3-3", "4-4-2", "3-5-2", "4-2-3-1", "5-3-2", "3-4-2-1"]:
            tk.Button(menu_frame, text=fmt, command=lambda f=fmt: self.change_team_formation("away", f)).pack(side=tk.LEFT)
        tk.Button(menu_frame, text="+控え", command=lambda: self.add_substitutes("away"), bg="#f0f0f0").pack(side=tk.LEFT, padx=2)

        # 保存・読込
        tk.Button(menu_frame, text="💾 保存", command=self.save_board).pack(side=tk.RIGHT, padx=5)
        tk.Button(menu_frame, text="📂 読込", command=self.load_board).pack(side=tk.RIGHT)
        tk.Button(menu_frame, text="✨ 新規", command=self.reset_board).pack(side=tk.RIGHT, padx=5)

        # --- キャンバス設定 ---
        self.w, self.h = self.WIDTH, self.HEIGHT
        self.canvas = tk.Canvas(root, width=self.w, height=self.h, bg=self.PITCH_COLOR)
        self.canvas.pack()

        # チームごとのスタイル（全体統一用）
        self.team_styles = {
            "home": {"bg": "white", "fg": "black"},
            "away": {"bg": "blue", "fg": "white"},
            "ball": {"bg": "white", "fg": "black"}
        }
        
        self.draw_pitch()
        
        # ドラッグ管理用
        self.current_tag = None
        self.drag_data = {"x": 0, "y": 0}
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.selected_tags = []
        self.selection_rect = None
        self.is_moving_group = False
        self.canvas.bind("<Button-1>", self.on_bg_click)
        self.canvas.bind("<B1-Motion>", self.on_bg_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_bg_release)

        # 初期配置
        self.change_team_formation("home", "4-3-3")
        self.change_team_formation("away", "4-3-3")
        self.create_player(425, 250, "", "BALL", "ball")

    def draw_pitch(self):
        c = self.canvas
        c.create_rectangle(25, 25, 825, 475, outline="white", width=2) # 外枠
        c.create_line(425, 25, 425, 475, fill="white", width=2) # センター
        c.create_oval(365, 190, 485, 310, outline="white", width=2) # センターサークル
        c.create_rectangle(25, 125, 145, 375, outline="white", width=2) # 左PA
        c.create_rectangle(705, 125, 825, 375, outline="white", width=2) # 右PA
        
        c.create_rectangle(0, 500, self.w, self.h, fill=self.FOOTER_COLOR, outline="") 
        c.create_text(425, 515, text="=== TACTICAL BOARD / AUTO-SAVED ===", fill="#ccc", font=("Arial", 9, "bold"))

    def create_player(self, x, y, num, name, team_tag, role="", memo=""):
        tag = f"p_{team_tag}_{int(time.time() * 1000)}_{num}"
        style = self.team_styles.get(team_tag, self.team_styles["ball"])
        t_color = style["fg"]

        # ボールの場合はサイズを小さく、名前の表示位置を調整
        is_player = team_tag in ["home", "away"]
        r = 18 if is_player else 10
        name_y_offset = 28 if is_player else 20
        role_y_offset = name_y_offset + 14

        self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=style["bg"], outline="black", tags=(tag, "icon", team_tag))
        self.canvas.create_text(x, y, text=num, fill=t_color, font=("Arial", 10, "bold"), tags=(tag, "num", team_tag))
        self.canvas.create_text(x, y+name_y_offset, text=name, fill=t_color, font=("Arial", 9, "bold"), tags=(tag, "name", team_tag))
        self.canvas.create_text(x, y+role_y_offset, text=role, fill=t_color, font=("Arial", 8, "italic"), tags=(tag, "role", team_tag), state='hidden')
        self.canvas.create_text(x, y, text=memo, state='hidden', tags=(tag, "memo", team_tag)) # メモは隠しテキストとして保持

        self.canvas.tag_bind(tag, "<Button-1>", self.on_click)
        self.canvas.tag_bind(tag, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(tag, "<ButtonRelease-1>", lambda e: self.auto_save())
        self.canvas.tag_bind(tag, "<Button-3>", lambda e: self.delete_player(tag))
        self.canvas.tag_bind(tag, "<Double-Button-1>", lambda e: self.edit_player(tag))

    def change_team_formation(self, team, fmt):
        self.canvas.delete(team)
        self.selected_tags = []
        
        # 座標データ（ホーム基準：左向き）
        pos_data = {
            "4-3-3": [(60,250), (150,100), (150,200), (150,300), (150,400), (240,150), (240,250), (240,350), (350,100), (350,250), (350,400)],
            "4-4-2": [(60,250), (150,100), (150,200), (150,300), (150,400), (250,80), (250,190), (250,310), (250,420), (380,200), (380,300)],
            "3-5-2": [(60,250), (140,150), (140,250), (140,350), (250,50), (230,150), (250,250), (230,350), (250,450), (380,200), (380,300)],
            "4-2-3-1": [(60,250), (150,100), (150,200), (150,300), (150,400), (230,200), (230,300), (320,100), (320,250), (320,400), (400,250)],
            "5-3-2": [(60,250), (140,80), (140,170), (140,250), (140,330), (140,420), (250,150), (250,250), (250,350), (380,180), (380,320)],
            "3-4-2-1": [(60,250), (140,150), (140,250), (140,350), (230,80), (230,190), (230,310), (230,420), (330,180), (330,320), (410,250)]
        }
        
        raw_pos = pos_data[fmt]
        prefix = "H" if team == "home" else "A"
        
        for i, (px, py) in enumerate(raw_pos):
            final_x = px if team == "home" else 850 - px
            self.create_player(final_x, py, str(i+1), f"{prefix}_{i+1}", team)
        
        self.auto_save()

    def add_substitutes(self, team):
        """11人の控え選手をフッターエリアに生成する"""
        prefix = "H" if team == "home" else "A"
        start_x = 40 if team == "home" else 470
        
        # 11人の控え選手を2列で配置
        for i in range(11):
            if i < 6:
                # 1列目 (6人)
                px = start_x + (i * 65)
                py = 560
            else:
                # 2列目 (5人)
                px = start_x + 32 + ((i - 6) * 65)
                py = 615
            
            num = 12 + i
            self.create_player(px, py, str(num), f"{prefix}_{num}", team)
        self.auto_save()

    def auto_save(self):
        data = {
            "players": self.get_board_data()
        }
        try:
            with open(self.TEMP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except IOError:
            pass # 自動保存の失敗はユーザーを邪魔しない程度に流す

    def get_board_data(self):
        data = []
        for item in self.canvas.find_withtag("icon"):
            tags = self.canvas.gettags(item)
            p_tag = next((t for t in tags if t.startswith("p_")), None)
            team_tag = "home" if "home" in tags else ("away" if "away" in tags else "ball")
            x1, y1, x2, y2 = self.canvas.coords(item)
            num, name, role, memo = "", "", "", ""
            for t_item in self.canvas.find_withtag(p_tag):
                t_tags = self.canvas.gettags(t_item)
                if "num" in t_tags: num = self.canvas.itemcget(t_item, "text")
                if "name" in t_tags: name = self.canvas.itemcget(t_item, "text")
                if "role" in t_tags: role = self.canvas.itemcget(t_item, "text")
                if "memo" in t_tags: memo = self.canvas.itemcget(t_item, "text")
            text_color = self.team_styles.get(team_tag, {"fg": "white"})["fg"]
            data.append({"x": (x1+x2)/2, "y": (y1+y2)/2, "num": num, "name": name, "role": role, "memo": memo, "color": self.canvas.itemcget(item, "fill"), "text_color": text_color, "team": team_tag})
        return data

    def save_board(self):
        if self.current_file_path:
            file_path = self.current_file_path
        else:
            file_path = filedialog.asksaveasfilename(defaultextension=".json")

        if file_path:
            try:
                full_data = {
                    "players": self.get_board_data()
                }
                with open(file_path, 'w', encoding="utf-8") as f:
                    json.dump(full_data, f, ensure_ascii=False, indent=4)
                self.current_file_path = file_path # 保存成功時にパスを更新
                messagebox.showinfo("保存", "保存が完了しました。")
            except Exception as e:
                messagebox.showerror("エラー", f"保存に失敗しました: {e}")

    def load_board(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            try:
                with open(file_path, 'r', encoding="utf-8") as f:
                    data = json.load(f)
                self.canvas.delete("home", "away", "ball")
                
                # 新旧フォーマットへの対応
                if isinstance(data, dict):
                    players = data.get("players", [])
                else:
                    players = data
                
                for p in players:
                    team = p['team']
                    if team in self.team_styles:
                        self.team_styles[team]['bg'] = p['color']
                        if 'text_color' in p:
                            self.team_styles[team]['fg'] = p['text_color']
                    self.create_player(p['x'], p['y'], p['num'], p['name'], team, p.get('role', ""), p.get('memo', ""))
                self.current_file_path = file_path # 読込成功時にパスを更新
                messagebox.showinfo("読込", "読込が完了しました。") # 読込成功メッセージを追加
            except Exception as e:
                messagebox.showerror("エラー", f"読込に失敗しました: {e}")

    def reset_board(self):
        """ボードを初期状態にリセットする"""
        if messagebox.askyesno("新規作成", "現在のボードをリセットして新規作成しますか？"):
            self.canvas.delete("home", "away", "ball")
            self.selected_tags = []
            self.current_file_path = None
            self.change_team_formation("home", "4-3-3")
            self.change_team_formation("away", "4-3-3")
            self.create_player(425, 250, "", "BALL", "ball")
            self.auto_save()

    def edit_player(self, tag):
        # 現在の情報を取得
        name, num, role, memo, team_label, team_tag = "", "", "", "", "Ball/Neutral", "ball"
        items = self.canvas.find_withtag(tag)
        
        for item in items:
            tags = self.canvas.gettags(item)
            if "num" in tags: num = self.canvas.itemcget(item, "text")
            elif "name" in tags: name = self.canvas.itemcget(item, "text")
            elif "role" in tags: role = self.canvas.itemcget(item, "text")
            elif "memo" in tags: memo = self.canvas.itemcget(item, "text")
            if "icon" in tags: current_color = self.canvas.itemcget(item, "fill")
            if "home" in tags: team_label = "Home Team"
            elif "away" in tags: team_label = "Away Team"

        if "home" in team_label.lower(): team_tag = "home"
        elif "away" in team_label.lower(): team_tag = "away"

        current_style = self.team_styles[team_tag]

        # プロフィール用ポップアップウィンドウ (Toplevel) の作成
        win = tk.Toplevel(self.root)
        win.title("選手プロファイル編集")
        win.resizable(False, False)
        win.grab_set()  # モーダル表示

        tk.Label(win, text="選手プロファイル", font=("Arial", 11, "bold")).pack(pady=10)
        tk.Label(win, text=f"所属: {team_label}", fg="gray").pack()

        tk.Label(win, text="選手名:").pack(pady=(10, 0))
        name_ent = tk.Entry(win, justify="center")
        name_ent.insert(0, name)
        # ボールの場合は名前の変更を不可にする
        if team_label == "Ball/Neutral":
            name_ent.config(state='disabled')
        name_ent.pack()

        tk.Label(win, text="背番号:").pack(pady=(10, 0))
        num_ent = tk.Entry(win, justify="center", width=5)
        num_ent.insert(0, num); num_ent.pack()

        tk.Label(win, text="役割 (FW, MF等):").pack(pady=(10, 0))
        role_ent = tk.Entry(win, justify="center", width=10)
        role_ent.insert(0, role); role_ent.pack()

        tk.Label(win, text="メモ:").pack(pady=(10, 0))
        memo_ent = tk.Entry(win, justify="center", width=30)
        memo_ent.insert(0, memo); memo_ent.pack()

        tk.Label(win, text="ユニフォーム色:").pack(pady=(10, 0))
        color_var = tk.StringVar(value=current_style["bg"])
        
        def choose_color():
            color = colorchooser.askcolor(initialcolor=color_var.get())[1]
            if color:
                color_var.set(color)
                color_preview.configure(bg=color)

        color_preview = tk.Frame(win, width=40, height=20, bg=current_style["bg"], highlightbackground="black", highlightthickness=1)
        color_preview.pack(pady=2)
        tk.Button(win, text="色を選択", command=choose_color).pack()

        tk.Label(win, text="文字色:").pack(pady=(10, 0))
        fg_var = tk.StringVar(value=current_style["fg"])
        fg_frame = tk.Frame(win)
        fg_frame.pack()
        tk.Radiobutton(fg_frame, text="白", variable=fg_var, value="white").pack(side=tk.LEFT)
        tk.Radiobutton(fg_frame, text="黒", variable=fg_var, value="black").pack(side=tk.LEFT)

        def update():
            new_bg = color_var.get()
            new_fg = fg_var.get()
            
            # 個別情報（名前・番号）の更新
            for item in items:
                t = self.canvas.gettags(item)
                if "name" in t: self.canvas.itemconfig(item, text=name_ent.get())
                if "num" in t: self.canvas.itemconfig(item, text=num_ent.get())
                if "role" in t: self.canvas.itemconfig(item, text=role_ent.get())
                if "memo" in t: self.canvas.itemconfig(item, text=memo_ent.get())
            
            # チーム全体のスタイルを更新
            self.team_styles[team_tag]["bg"] = new_bg
            self.team_styles[team_tag]["fg"] = new_fg
            self.apply_team_styles(team_tag)
            
            self.auto_save()
            win.destroy()

        tk.Button(win, text="保存して閉じる", command=update, bg="#2e8b57", fg="white").pack(pady=20)

    def apply_team_styles(self, team_tag):
        style = self.team_styles[team_tag]
        for item in self.canvas.find_withtag(team_tag):
            tags = self.canvas.gettags(item)
            if "icon" in tags: self.canvas.itemconfig(item, fill=style["bg"])
            elif "num" in tags or "name" in tags or "role" in tags: self.canvas.itemconfig(item, fill=style["fg"])

    def delete_player(self, tag):
        # 削除前に選手名を取得（確認メッセージ用）
        name = "選手"
        for item in self.canvas.find_withtag(tag):
            if "name" in self.canvas.gettags(item):
                name = self.canvas.itemcget(item, "text")
                break

        if messagebox.askyesno("削除の確認", f"'{name}' を削除してもよろしいですか？"):
            self.canvas.delete(tag)
            if tag in self.selected_tags: self.selected_tags.remove(tag)
            self.auto_save()

    def on_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        tags = self.canvas.gettags(item)
        tag = next((t for t in tags if t.startswith("p_")), None)

        if tag:
            is_shift = event.state & 0x1
            if is_shift:
                if tag in self.selected_tags:
                    self.selected_tags.remove(tag)
                else:
                    self.selected_tags.append(tag)
            else:
                if tag not in self.selected_tags:
                    self.selected_tags = [tag]
            
            self.update_selection_visuals()
            self.drag_data = {"x": event.x, "y": event.y}
            return "break" # 背景クリックのイベントを発火させない

    def on_drag(self, event):
        if self.selected_tags:
            dx, dy = event.x - self.drag_data["x"], event.y - self.drag_data["y"]
            for tag in self.selected_tags:
                self.canvas.move(tag, dx, dy)
            self.drag_data["x"], self.drag_data["y"] = event.x, event.y
            return "break"

    def deselect_all(self, event):
        self.selected_tags = []
        self.update_selection_visuals()

    def get_selection_bbox(self):
        """現在選択されている全選手のバウンディングボックスを取得"""
        if not self.selected_tags:
            return None
        
        x_coords = []
        y_coords = []
        for tag in self.selected_tags:
            bbox = self.canvas.bbox(tag) # (x1, y1, x2, y2)
            if bbox:
                x_coords.extend([bbox[0], bbox[2]])
                y_coords.extend([bbox[1], bbox[3]])
        
        if not x_coords: return None
        return min(x_coords), min(y_coords), max(x_coords), max(y_coords)

    def on_bg_click(self, event):
        # 既存の選択範囲内をクリックしたかチェック
        bbox = self.get_selection_bbox()
        if bbox and bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
            self.is_moving_group = True
            self.drag_data = {"x": event.x, "y": event.y}
        else:
            self.is_moving_group = False
            self.deselect_all(event)
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
            # 選択用の矩形を作成
            self.selection_rect = self.canvas.create_rectangle(
                event.x, event.y, event.x, event.y, outline="yellow", dash=(4, 4)
            )

    def on_bg_drag(self, event):
        if self.is_moving_group:
            # 選択範囲全体を移動
            dx, dy = event.x - self.drag_data["x"], event.y - self.drag_data["y"]
            for tag in self.selected_tags:
                self.canvas.move(tag, dx, dy)
            self.drag_data["x"], self.drag_data["y"] = event.x, event.y
        elif self.selection_rect:
            self.canvas.coords(self.selection_rect, self.drag_start_x, self.drag_start_y, event.x, event.y)

    def on_bg_release(self, event):
        if self.is_moving_group:
            self.auto_save()
            return

        if self.selection_rect:
            coords = self.canvas.coords(self.selection_rect)
            # 枠に重なっているアイテムを取得 (find_overlapping)
            overlapping = self.canvas.find_overlapping(min(coords[0], coords[2]), min(coords[1], coords[3]), 
                                                     max(coords[0], coords[2]), max(coords[1], coords[3]))
            for item in overlapping:
                tags = self.canvas.gettags(item)
                if "icon" in tags:
                    p_tag = next((t for t in tags if t.startswith("p_")), None)
                    if p_tag and p_tag not in self.selected_tags:
                        self.selected_tags.append(p_tag)
            
            self.update_selection_visuals()
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None

    def update_selection_visuals(self):
        for item in self.canvas.find_withtag("icon"):
            tags = self.canvas.gettags(item)
            p_tag = next((t for t in tags if t.startswith("p_")), None)
            if p_tag in self.selected_tags:
                self.canvas.itemconfig(item, outline="yellow", width=3)
            else:
                self.canvas.itemconfig(item, outline="black", width=1)

if __name__ == "__main__":
    root = tk.Tk()
    app = TacticalBoard(root)
    root.mainloop()

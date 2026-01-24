import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, RegularPolygon
from matplotlib.projections.polar import PolarAxes
from matplotlib.projections import register_projection
from matplotlib import font_manager
import os

# 字体配置
font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
prop = font_manager.FontProperties(fname=font_path)
plt.rcParams['font.family'] = prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

def radar_factory(num_vars, frame='circle'):
    theta = np.linspace(0, 2*np.pi, num_vars, endpoint=False)
    
    class RadarAxes(PolarAxes):
        name = 'radar'
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.set_theta_zero_location('N')

        def fill(self, *args, closed=True, **kwargs):
            return super().fill(closed=closed, *args, **kwargs)

        def plot(self, *args, **kwargs):
            lines = super().plot(*args, **kwargs)
            for line in lines:
                self._close_line(line)

        def _close_line(self, line):
            x, y = line.get_data()
            if x[0] != x[-1]:
                x = np.append(x, x[0])
                y = np.append(y, y[0])
                line.set_data(x, y)

        def set_varlabels(self, labels):
            self.set_thetagrids(np.degrees(theta), labels, fontproperties=prop)

        def _gen_axes_patch(self):
            if frame == 'circle':
                return Circle((0.5, 0.5), 0.5)
            elif frame == 'polygon':
                return RegularPolygon((0.5, 0.5), num_vars, radius=.5, edgecolor="k")
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)

    register_projection(RadarAxes)
    return theta

def generate_chart():
    # 维度调整：超脱 -> 相貌 (Appearance)
    labels = ['智性 (Intelligence)', '能动性 (Agency)', '神性 (Divinity)', '野心 (Ambition)', '相貌 (Appearance)']
    
    # 数据重估
    data = {
        '曦 (Xi)':      [95, 80, 100, 40, 95],  # 完美的白月光
        '夏 (Summer)':  [90, 100, 90, 80, 90],  # 充满活力的美
        '初蝉 (Chu Chan)': [98, 90, 40, 95, 99], # 倾国倾城的武器
        '安宁 (An Ning)': [85, 85, 60, 90, 92],  # 冷艳气质
        '万露 (Wan Lu)':  [40, 30, 20, 50, 85]   # 唯一的亮点是好看
    }
    
    N = len(labels)
    theta = radar_factory(N, frame='polygon')
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='radar'))
    fig.patch.set_facecolor('#050510')
    ax.set_facecolor('#050510')
    
    colors = {
        '曦 (Xi)': '#00FFFF',      # Cyan
        '夏 (Summer)': '#FF4500',  # OrangeRed
        '初蝉 (Chu Chan)': '#FFD700', # Gold
        '安宁 (An Ning)': '#FF69B4',  # HotPink
        '万露 (Wan Lu)': '#808080'    # Gray
    }

    # 调整绘制顺序，让万露在最上面，凸显她的“单刺”结构
    sorted_keys = ['曦 (Xi)', '夏 (Summer)', '初蝉 (Chu Chan)', '安宁 (An Ning)', '万露 (Wan Lu)']

    for name in sorted_keys:
        values = data[name]
        # 万露用白色虚线高亮，或者保持灰色但加粗
        lw = 3 if 'Wan Lu' in name else 2
        ax.plot(theta, values, color=colors[name], linewidth=lw, label=name)
        ax.fill(theta, values, facecolor=colors[name], alpha=0.15)
        
    ax.set_varlabels(labels)
    
    ax.tick_params(axis='x', colors='white', labelsize=12)
    ax.tick_params(axis='y', colors='#666666', labelsize=8)
    
    ax.grid(color='#333333')
    ax.spines['polar'].set_visible(False)
    
    legend = ax.legend(loc=(0.9, .95), labelspacing=0.1, fontsize=10, facecolor='#1a1a1a', edgecolor='#333333', prop=prop)
    for text in legend.get_texts():
        text.set_color("white")
        
    plt.title("Soul Spectrum Radar (Appearance)", color='white', size=20, y=1.05, fontproperties=prop)
    
    output_path = os.path.expanduser("~/pob_server/uploads/soul_radar_appearance.png")
    plt.savefig(output_path, facecolor='#050510', bbox_inches='tight')
    print(f"Generated: {output_path}")

if __name__ == "__main__":
    generate_chart()

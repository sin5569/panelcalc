import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("☀️ Подбор солнечных панелей под инвертор (с поддержкой 1–3 MPPT)")

# ===== Входные данные =====
with st.sidebar:
    st.header("⚙️ Параметры инвертора")
    inv_power_ac = st.number_input("Мощность MPPT инвертора (AC), кВт", min_value=0.0, value=5.0, step=0.1)
    vdc_max = st.number_input("Предел входного напряжения инвертора (Vdc_max), В", min_value=0.0, value=1000.0, step=1.0)
    mppt_v_min = st.number_input("Минимальное входное напряжение инвертора (MPPT V_min), В", min_value=0.0, value=200.0, step=1.0)
    mppt_v_max = st.number_input("Максимальное входное напряжение инвертора (MPPT V_max), В", min_value=0.0, value=850.0, step=1.0)
    mppt_count = st.selectbox("Количество MPPT-входов", [1, 2, 3], index=1)
    idc_max = st.number_input("Макс. DC ток на один MPPT, А", min_value=0.0, value=15.0, step=0.1)
    inv_eff = st.slider("КПД инвертора", 0.5, 1.0, 0.97, 0.01)

st.header("Параметры панели")
panel_p = st.number_input("Максимальная мощность панели W (Pmax)", min_value=1.0, value=410.0)
panel_vmp = st.number_input("Рабочее напряжение панели V (Vmp)", min_value=0.0, value=34.0)
panel_imp = st.number_input("Ток при максимальной мощности панели A(Imp)", min_value=0.0, value=12.0)
panel_voc = st.number_input("Напряжение холостого хода панели V (Voc)", min_value=0.0, value=41.0)
panel_isc = st.number_input("Сила тока короткого замыкания панели А (Isc)", min_value=0.0, value=12.8)
temp_cell_min = st.number_input("Мин. температура, °C", value=-10.0, step=1.0)
temp_coeff_voc = st.number_input("Коэф. Voc (%/°C) как дробь", value=-0.003, step=0.0001, format="%.4f")
safety_margin = st.number_input("Запас по Voc (%)", value=5.0, step=0.1)

# ===== Функции =====
def voc_at_temp(voc_stc, temp_c, coeff):
    return voc_stc * (1 + coeff * (temp_c - 25.0))

def calc_for_mppt(n_series, n_parallel, vdc_max, mppt_v_min, mppt_v_max, idc_max):
    voc_temp = voc_at_temp(panel_voc, temp_cell_min, temp_coeff_voc)
    voc_temp *= 1.0 + safety_margin/100
    string_voc = voc_temp * n_series
    string_vmp = panel_vmp * n_series
    string_imp = panel_imp * n_parallel

    issues = []
    if string_voc > vdc_max:
        issues.append("❌Voc строки превышает Vdc_max")
    if string_vmp < mppt_v_min:
        issues.append("❌Vmp ниже MPPT диапазона")
    if string_vmp > mppt_v_max:
        issues.append("❌Vmp выше MPPT диапазона")
    if string_imp > idc_max:
        issues.append("❌Ток превышает лимит MPPT")

    power_dc = panel_p * n_series * n_parallel
    return {
        "Напр. холостого хода Voc": string_voc,
        "Рабочее напр. Vmp": string_vmp,
        "Ток при макс. мощности Imp": string_imp,
        "Ватт на один MPPT": power_dc,
        "Проблема": "; ".join(issues) if issues else "OK"
    }

def draw_scheme(n_series, n_parallel_per_mppt, mppt_count):
    fig, ax = plt.subplots(figsize=(8, 2 + mppt_count*2), facecolor='none')  # прозрачный фон
    ax.set_xlim(0, n_series + 2)
    ax.set_ylim(0, mppt_count*(n_parallel_per_mppt + 1))
    ax.axis('off')

    # Инвертор
    ax.add_patch(plt.Rectangle((n_series + 1, 0), 1, mppt_count*(n_parallel_per_mppt + 1),
                               color="white", alpha=0.3))
    ax.text(n_series + 1.5, mppt_count*(n_parallel_per_mppt + 1)/2, "INV",
            ha='center', va='center', fontsize=12)

    # Панели
    for mppt_idx in range(mppt_count):
        y_offset = mppt_idx*(n_parallel_per_mppt + 1)
        for par_idx in range(n_parallel_per_mppt):
            y = y_offset + par_idx + 0.5
            for series_idx in range(n_series):
                rect = plt.Rectangle((series_idx, y), 0.8, 0.4, color='skyblue')
                ax.add_patch(rect)
                if series_idx == 0:
                    ax.text(series_idx-0.2, y+0.2, f"MPPT{mppt_idx+1}", va='center',
                            ha='right', fontsize=8)
            # Линия к инвертору
            ax.plot([n_series, n_series+1], [y+0.2, y+0.5], color='white', linewidth=1)

    st.pyplot(fig, clear_figure=True)

# ===== Автоподбор числа параллельных строк =====
st.header("📊 Автоподбор количества параллельных строк (DC/AC ~ 1.2)")
target_ratio = 1.2
default_n_series = 10
n_parallel_calc = max(1, round((inv_power_ac * 1000 * target_ratio) / (panel_p * default_n_series * mppt_count)))
st.write(f"Рекомендуемое количество параллельных строк на один MPPT: **{n_parallel_calc}**")

# Пользователь может изменить вручную
n_series = st.number_input("Панелей в строке", min_value=1, value=default_n_series)
n_parallel_per_mppt = st.number_input("Параллельных строк на один MPPT", min_value=1, value=n_parallel_calc)

# ===== Расчёт =====
if st.button("Рассчитать"):
    results = []
    total_power_dc = 0
    for mppt in range(1, mppt_count+1):
        res = calc_for_mppt(n_series, n_parallel_per_mppt, vdc_max, mppt_v_min, mppt_v_max, idc_max)
        total_power_dc += res["Ватт на один MPPT"]
        res["mppt"] = f"MPPT {mppt}"
        results.append(res)

    df = pd.DataFrame(results)

    # 🔌 Рисуем интерактивную схему подключения
    st.subheader("Схема подключения панелей к инвертору")
    draw_scheme(n_series, n_parallel_per_mppt, mppt_count)

    # Таблица результатов
    st.subheader("📑 Результаты по каждому MPPT")
    st.dataframe(df)

    # Итог по системе
    st.subheader("⚡ Итог:")
    st.write(f"Всего панелей: **{n_series * n_parallel_per_mppt * mppt_count} шт.**")
    st.write(f"Суммарная мощность DC: **{total_power_dc/1000:.2f} кВт**")
    st.write(f"Оценка мощности AC (с КПД {inv_eff*100:.1f}%): **{total_power_dc*inv_eff/1000:.2f} кВт**")

    # DC/AC коэффициент
    dc_ac_ratio = total_power_dc / (inv_power_ac * 1000)
    st.write(f"DC/AC коэффициент: **{dc_ac_ratio:.2f}**")
    if dc_ac_ratio > 1.3:
        st.warning("❌DC/AC коэффициент слишком большой (>1.3). Возможны потери на клиппинге.")
    elif dc_ac_ratio < 1.0:
        st.info("ℹ️ DC/AC коэффициент меньше 1.0 — инвертор недогружен")
    else:
        st.success("✅ DC/AC коэффициент в оптимальном диапазоне")

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("🔋Калькулятор автономности LiFePO₄ батарей")

# --- Ввод параметров пользователем ---
st.sidebar.header("Настройки батарей и нагрузки")

# Названия батарей
battery_names = st.sidebar.text_area(
    "Названия батарей (через запятую)", 
    value="52.1В 5 кВтч, 52.1В 10 кВтч, 52.1В 15 кВтч, 52.1В 20 кВтч"
).split(",")

# Ёмкость батарей
capacities = st.sidebar.text_area(
    "Ёмкость батарей (кВт·ч, через запятую, в том же порядке)", 
    value="5, 10, 15"
).split(",")
capacities = [float(c.strip()) for c in capacities]

# DOD
DOD = st.sidebar.slider("Глубина разряда (DOD, %)", 0, 100, 80) / 100

# Нагрузки
loads_input = st.sidebar.text_area(
    "Нагрузки (Вт, через запятую)", 
    value="250,400,550,800,1000,1500,2000"
)
loads = [int(l.strip()) for l in loads_input.split(",")]

# --- Расчёт часов работы ---
batteries = {name.strip(): cap for name, cap in zip(battery_names, capacities)}
df = pd.DataFrame(index=batteries.keys(), columns=[f"{l} Вт" for l in loads], dtype=float)

for bat_name, bat_kwh in batteries.items():
    usable_wh = bat_kwh * 1000 * DOD
    for load in loads:
        df.loc[bat_name, f"{load} Вт"] = round(usable_wh / load, 2)

# --- Построение графика ---
st.subheader("График часов автономной работы")
df_plot = df.T

fig, ax = plt.subplots(figsize=(10, 5))
df_plot.plot(kind='bar', ax=ax, rot=0)
ax.set_ylabel("Часы автономной работы")
ax.set_xlabel("Нагрузка")
ax.set_title(f"Сравнение времени автономной работы батарей (LiFePO₄, DOD {int(DOD*100)}%)")
ax.grid(axis='y', linestyle='--', linewidth=0.5)
st.pyplot(fig)

# --- Таблица под графиком ---
st.subheader("Таблица часов автономной работы")
st.dataframe(df)

plt.tight_layout()
plt.savefig("battery_autonomy_graph_and_table_dod80.png")
plt.show()

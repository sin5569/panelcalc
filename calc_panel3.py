import streamlit as st
import math
import pandas as pd

st.set_page_config(layout="wide")
st.title("⚡️ Подбор солнечных панелей под инвертор (с поддержкой 1–3 MPPT)")

# ===== Входные данные =====
with st.sidebar:
    st.header("⚙️ Параметры инвертора")
    inv_power_ac = st.number_input("Мощность инвертора (AC), кВт", min_value=0.0, value=5.0, step=0.1)
    vdc_max = st.number_input("Предел входного напряжения инвертора (Vdc_max), В", min_value=0.0, value=1000.0, step=1.0)
    mppt_v_min = st.number_input("Минимальное входное напряжение инвертора (MPPT V_min), В", min_value=0.0, value=200.0, step=1.0)
    mppt_v_max = st.number_input("Максимальное входное напряжение инвертора (MPPT V_max), В", min_value=0.0, value=850.0, step=1.0)
    mppt_count = st.selectbox("Количество MPPT-входов", [1, 2, 3], index=1)
    idc_max = st.number_input("Макс. DC ток на один MPPT, А", min_value=0.0, value=15.0, step=0.1)
    inv_eff = st.slider("КПД инвертора", 0.5, 1.0, 0.97, 0.01)

st.header("☀️ Параметры панели")
panel_p = st.number_input("Максимальная мощность солнечной панели W (Pmax)", min_value=1.0, value=410.0)
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

    ok = True
    issues = []
    if string_voc > vdc_max:
        ok = False
        issues.append("❌Voc строки превышает Vdc_max")
    if string_vmp < mppt_v_min:
        issues.append("❌Vmp ниже MPPT диапазона")
    if string_vmp > mppt_v_max:
        issues.append("❌Vmp выше MPPT диапазона")
    if string_imp > idc_max:
        issues.append("❌Ток превышает лимит MPPT")

    power_dc = panel_p * n_series * n_parallel
    return {
        "ok": ok,
        "voc": string_voc,
        "vmp": string_vmp,
        "imp": string_imp,
        "power_dc": power_dc,
        "issues": "; ".join(issues) if issues else "OK"
    }

# ===== Расчёт =====
st.header("📊 Расчёт конфигурации")

n_series = st.number_input("Панелей в строке", min_value=1, value=10)
n_parallel_per_mppt = st.number_input("Параллельных строк на один MPPT", min_value=1, value=2)

if st.button("Рассчитать"):
    results = []
    total_power_dc = 0
    for mppt in range(1, mppt_count+1):
        res = calc_for_mppt(n_series, n_parallel_per_mppt, vdc_max, mppt_v_min, mppt_v_max, idc_max)
        total_power_dc += res["power_dc"]
        res["mppt"] = f"MPPT {mppt}"
        results.append(res)

    df = pd.DataFrame(results)
    st.dataframe(df)

    st.subheader("⚡ Итог по системе")
    st.write(f"Всего панелей: **{n_series * n_parallel_per_mppt * mppt_count} шт.**")
    st.write(f"Суммарная мощность DC: **{total_power_dc/1000:.2f} кВт**")
    st.write(f"Оценка мощности AC (с КПД {inv_eff*100:.1f}%): **{total_power_dc*inv_eff/1000:.2f} кВт**")

    if total_power_dc/1000 > inv_power_ac*1.3:
        st.warning("❌DC/AC коэффициент слишком большой (>1.3). Возможны потери на клиппинге.")

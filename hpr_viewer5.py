import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import datetime
import xml.dom.minidom
import matplotlib.pyplot as plt

st.title("hprファイル簡易ビューア v0.1")
st.markdown("""
**試作中です。**  
- StanForDやアプリのバージョンへの確認はこれからです。  
- hprファイルから幹ごとに丸太データの確認  
- 幹範囲指定＋CSV出力機能  
<br>
**作成者：KITARINラボ**
""")

# --- 注意喚起 ---
st.markdown("""
#### 【利用にあたっての注意・同意事項】
- アップロードしたhprファイルは、セッションごとに自分だけしか見えず、サーバーにも残りません。
- ただし**特段のセキュリティ管理はできていません**ので、**個人情報を含むファイルのアップロードはご遠慮ください**。
- パスワード認証は現在利用できません。URLを知っている関係者のみご利用ください。
""")
# agree = st.checkbox("上記の注意事項を確認し、同意します")
# if not agree:
#     st.warning("同意チェックを入れてからご利用ください。")
#     st.stop()

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 🟡 hprファイル（StanForD XML）を選択してください")
uploaded_file = st.file_uploader("", type="hpr")

def calc_matsukuchi(top_ub_mm, length_cm):
    """末口二乗法：材積 = (末口径[m])^2 × 長さ[m]"""
    try:
        d_m = float(top_ub_mm) / 1000   # mm → m
        l_m = float(length_cm) / 100    # cm → m
        return round(d_m ** 2 * l_m, 4)
    except:
        return ""

if uploaded_file is not None:
    # ファイルサイズ
    file_size = uploaded_file.size
    file_size_kb = f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.2f} MB"
    upload_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # XMLパース
    tree = ET.parse(uploaded_file)
    root = tree.getroot()
    ns = {'sf': 'urn:skogforsk:stanford2010'}

    # StanForDバージョン・アプリバージョン
    std_ver = root.attrib.get("version", "")
    creator = root.attrib.get("creator", "")

    # 幹数・丸太数
    stems = root.findall(".//sf:Stem", ns)
    logs = root.findall(".//sf:Log", ns)
    stem_count = len(stems)
    log_count = len(logs)

    # ファイル作成者・機械名（存在すれば）
    machine_elem = root.find(".//sf:MachineData", ns)
    manufacturer = machine_elem.findtext("sf:Manufacturer", default="", namespaces=ns) if machine_elem is not None else ""
    model = machine_elem.findtext("sf:Model", default="", namespaces=ns) if machine_elem is not None else ""
    serial = machine_elem.findtext("sf:SerialNumber", default="", namespaces=ns) if machine_elem is not None else ""
    operator = machine_elem.findtext("sf:Operator", default="", namespaces=ns) if machine_elem is not None else ""

    st.markdown("### ファイル情報・メタデータ")
    st.write(f"**ファイル名:** {uploaded_file.name}")
    st.write(f"**ファイルサイズ:** {file_size_kb}")
    st.write(f"**アップロード日時:** {upload_time}")
    st.write(f"**StanForDバージョン:** {std_ver if std_ver else '(不明)'}")
    st.write(f"**アプリバージョン/作成者:** {creator if creator else '(不明)'}")
    st.write(f"**幹（Stem）本数:** {stem_count}")
    st.write(f"**丸太（Log）本数:** {log_count}")

    if manufacturer or model or serial or operator:
        st.write("**機械情報:**")
        if manufacturer: st.write(f"・メーカー: {manufacturer}")
        if model: st.write(f"・機種: {model}")
        if serial: st.write(f"・シリアルNo.: {serial}")
        if operator: st.write(f"・オペレータ: {operator}")

    # --- メイン処理（範囲指定・テーブル・CSV出力など） ---
    stem_dict = {}
    stem_numbers = []
    for i, s in enumerate(stems):
        key = s.findtext("sf:StemKey", "", ns)
        num = i + 1
        if key:
            stem_numbers.append(num)
            stem_dict[num] = s

    # 範囲指定（スライダー）
    st.markdown("#### 幹データ番号の範囲を指定してください")
    start_num, end_num = st.select_slider(
        "範囲（開始〜終了）",
        options=stem_numbers,
        value=(stem_numbers[0], stem_numbers[-1])
    )

    # 幹ID選択表示（個別表示用）
    selected_num = st.selectbox(
        "個別表示したい幹（データ番号: 幹ID）を選んでください",
        stem_numbers,
        format_func=lambda x: f"{x}: {stem_dict[x].findtext('sf:StemKey', '', ns)}"
    )

    # 範囲指定された幹の全丸太データを集めてリスト化
    all_data = []
    for num in range(start_num, end_num + 1):
        stem = stem_dict[num]
        logs = stem.findall(".//sf:Log", ns)
        stem_key = stem.findtext("sf:StemKey", "", ns)
        for l in logs:
            log_key = l.findtext('sf:LogKey', '', ns)
            log_vols = l.findall('sf:LogVolume', ns)
            m3sub = m3price = m3sob = ""
            for v in log_vols:
                cat = v.attrib.get('logVolumeCategory', '')
                if cat == "m3sub":
                    m3sub = v.text
                elif cat == "m3 (price)":
                    m3price = v.text
                elif cat == "m3sob":
                    m3sob = v.text
            measurements = l.findall('sf:LogMeasurement', ns)
            length = ''
            top_diam = ''
            for m in measurements:
                for child in m:
                    if child.tag.endswith('LogLength') and not length:
                        length = child.text
                    if child.tag.endswith('LogDiameter'):
                        cat = child.attrib.get('logDiameterCategory', '')
                        if cat == "Top ub" and not top_diam:
                            top_diam = child.text
            matsukuchi = calc_matsukuchi(top_diam, length)
            top_diam_m = round(float(top_diam)/1000, 3) if top_diam else ""
            length_m = round(float(length)/100, 2) if length else ""
            all_data.append({
                "幹データ番号": num,
                "StemKey": stem_key,
                "LogKey": log_key,
                "長さ(m)": length_m,
                "末口径(m)": top_diam_m,
                "末口二乗法材積(m³)": matsukuchi,
                "m3sub": m3sub,
                "m3(price)": m3price,
                "m3sob": m3sob
            })

    df = pd.DataFrame(all_data)

    st.markdown(f"#### 幹データ番号 {start_num} 〜 {end_num} の丸太データ一覧")
    st.dataframe(df)

    # CSV出力ボタン
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="この範囲のデータをCSVでダウンロード",
        data=csv,
        file_name=f"hpr_logs_{start_num}-{end_num}.csv",
        mime="text/csv"
    )

    # --- ① 入力長さで絞り込み＋サマリー ---
    st.markdown("### 指定長さに近い丸太のサマリー")
    length_input = st.number_input("基準となる丸太の長さ（m）を入力してください", min_value=0.0, max_value=20.0, step=0.1, value=4.0)
    tol = 0.15  # ±15cm = ±0.15m

    # 長さ(m)の値が空欄でないものを対象に比較
    df_valid = df[df['長さ(m)'] != ""].copy()
    df_valid['長さ(m)'] = df_valid['長さ(m)'].astype(float)

    # 絞り込み
    near_df = df_valid[(df_valid['長さ(m)'] >= length_input - tol) & (df_valid['長さ(m)'] <= length_input + tol)]

    if len(near_df) > 0:
        mean_length = near_df['長さ(m)'].mean()
        mean_diam = pd.to_numeric(near_df['末口径(m)'], errors='coerce').mean()
        sum_vol = pd.to_numeric(near_df['末口二乗法材積(m³)'], errors='coerce').sum()
        st.success(f"【抽出本数: {len(near_df)}】")
        st.write(f"平均長さ: {mean_length:.2f} m")
        st.write(f"平均末口径: {mean_diam:.3f} m")
        st.write(f"合計材積（末口二乗法）: {sum_vol:.3f} m³")
    else:
        st.info("該当する丸太がありません。")

    # --- ② ヒストグラム/分布グラフ ---
    st.markdown("### 丸太の長さ・径・材積の分布（ヒストグラム）")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # 長さ
    lengths = pd.to_numeric(df['長さ(m)'], errors='coerce').dropna()
    axes[0].hist(lengths, bins=20)
    axes[0].set_title("長さ (m)")
    axes[0].set_xlabel("長さ(m)")
    axes[0].set_ylabel("本数")

    # 末口径
    diams = pd.to_numeric(df['末口径(m)'], errors='coerce').dropna()
    axes[1].hist(diams, bins=20)
    axes[1].set_title("末口径 (m)")
    axes[1].set_xlabel("径(m)")
    axes[1].set_ylabel("本数")

    # 材積
    vols = pd.to_numeric(df['末口二乗法材積(m³)'], errors='coerce').dropna()
    axes[2].hist(vols, bins=20)
    axes[2].set_title("材積 (m³)")
    axes[2].set_xlabel("材積(m³)")
    axes[2].set_ylabel("本数")

    plt.tight_layout()
    st.pyplot(fig)

    # --- 個別幹表示（テーブル＋XML抜粋） ---
    st.markdown("---")
    st.markdown("#### 選択した幹IDの丸太詳細・XML抜粋")
    stem = stem_dict[selected_num]
    logs = stem.findall(".//sf:Log", ns)
    data = []
    for l in logs:
        log_key = l.findtext('sf:LogKey', '', ns)
        log_vols = l.findall('sf:LogVolume', ns)
        m3sub = m3price = m3sob = ""
        for v in log_vols:
            cat = v.attrib.get('logVolumeCategory', '')
            if cat == "m3sub":
                m3sub = v.text
            elif cat == "m3 (price)":
                m3price = v.text
            elif cat == "m3sob":
                m3sob = v.text
        measurements = l.findall('sf:LogMeasurement', ns)
        length = ''
        top_diam = ''
        for m in measurements:
            for child in m:
                if child.tag.endswith('LogLength') and not length:
                    length = child.text
                if child.tag.endswith('LogDiameter'):
                    cat = child.attrib.get('logDiameterCategory', '')
                    if cat == "Top ub" and not top_diam:
                        top_diam = child.text
        matsukuchi = calc_matsukuchi(top_diam, length)
        top_diam_m = round(float(top_diam)/1000, 3) if top_diam else ""
        length_m = round(float(length)/100, 2) if length else ""
        data.append({
            "LogKey": log_key,
            "長さ(m)": length_m,
            "末口径(m)": top_diam_m,
            "末口二乗法材積(m³)": matsukuchi,
            "m3sub": m3sub,
            "m3(price)": m3price,
            "m3sob": m3sob
        })
    st.table(data)

    # XML抜粋
    st.subheader("この幹（Stem）のXMLデータ抜粋")
    raw_xml = ET.tostring(stem, encoding='utf-8')
    pretty_xml = xml.dom.minidom.parseString(raw_xml).toprettyxml(indent="  ")
    st.code(pretty_xml, language="xml")

else:
    st.info("まずはファイルをアップロードしてください")

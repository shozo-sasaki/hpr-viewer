import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

st.title("hprファイル簡易ビューア v0.1")
st.markdown("""
**試作中です。**  
- StanForDやアプリのバージョンへの確認はこれからです。  
- hprファイルから幹ごとに丸太データの確認  
- 幹範囲指定＋CSV出力機能  
<br>
**作成者：KITARINラボ**
""")

# --- 注意喚起と同意チェック ---
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
    ns = {'sf': 'urn:skogforsk:stanford2010'}
    tree = ET.parse(uploaded_file)
    root = tree.getroot()
    stems = root.findall(".//sf:Stem", ns)
    logs = root.findall(".//sf:Log", ns)
    st.success("ファイルを読み込みました")
    st.write(f"幹（Stem）本数: {len(stems)}")
    st.write(f"丸太（Log）本数: {len(logs)}")

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
            # 材積の複数カテゴリ
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
            # 長さ・径
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
            # 末口二乗法（日本式）
            matsukuchi = calc_matsukuchi(top_diam, length)
            # m単位変換
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

    # DataFrame化
    df = pd.DataFrame(all_data)

    # 範囲指定部分を画面にテーブル表示
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

    # 個別幹表示（テーブル＋XML抜粋）
    st.markdown("---")
    st.markdown("#### 選択した幹IDの丸太詳細・XML抜粋")
    stem = stem_dict[selected_num]
    logs = stem.findall(".//sf:Log", ns)
    data = []
    for l in logs:
        log_key = l.findtext('sf:LogKey', '', ns)
        # 材積の複数カテゴリ
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
        # 長さ・径
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
    import xml.dom.minidom
    st.subheader("この幹（Stem）のXMLデータ抜粋")
    raw_xml = ET.tostring(stem, encoding='utf-8')
    pretty_xml = xml.dom.minidom.parseString(raw_xml).toprettyxml(indent="  ")
    st.code(pretty_xml, language="xml")

else:
    st.info("まずはファイルをアップロードしてください")

# ...existing code...
"""
Plagiarism Detection System - Web Interface
"""

import streamlit as st
from pathlib import Path
import shutil
import tempfile
import re

from plagiarism_checker.pipeline import PipelineConfig, PlagiarismPipeline


st.set_page_config(
    page_title="Plagiarism Checker",
    page_icon="🔍",
    layout="wide",
)

# CSS styles
st.markdown("""
<style>
    .highlight-high {
        background-color: #ff6b6b;
        padding: 2px 4px;
        border-radius: 3px;
        cursor: pointer;
        display: inline-block;
        margin: 2px 0;
    }
    .highlight-medium {
        background-color: #ffd93d;
        padding: 2px 4px;
        border-radius: 3px;
        cursor: pointer;
        display: inline-block;
        margin: 2px 0;
    }
    .highlight-low {
        background-color: #a8e6cf;
        padding: 2px 4px;
        border-radius: 3px;
        cursor: pointer;
        display: inline-block;
        margin: 2px 0;
    }
    .highlight-citation {
        background-color: #d4a5ff;
        padding: 2px 4px;
        border-radius: 3px;
        cursor: pointer;
        display: inline-block;
        margin: 2px 0;
        border: 1px dashed #9d4edd;
    }
    .text-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 5px;
        line-height: 2;
        font-size: 16px;
        max-height: 600px;
        overflow-y: auto;
    }
    .student-name {
        font-size: 20px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 10px;
    }
    .target-file {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .reference-file {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
    }
    .legend-item {
        display: inline-block;
        margin-right: 20px;
        margin-bottom: 10px;
    }
    .legend-box {
        display: inline-block;
        width: 20px;
        height: 20px;
        border-radius: 3px;
        margin-right: 5px;
        vertical-align: middle;
    }
</style>
""", unsafe_allow_html=True)

# initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = None
if 'selected_pair' not in st.session_state:
    st.session_state.selected_pair = None
if 'target_file' not in st.session_state:
    st.session_state.target_file = None
if 'detection_mode' not in st.session_state:
    st.session_state.detection_mode = "all"  # "all" or "target"


def cleanup_temp():
    """Remove temporary files"""
    if st.session_state.temp_dir and Path(st.session_state.temp_dir).exists():
        shutil.rmtree(st.session_state.temp_dir)
        st.session_state.temp_dir = None


def save_uploaded_files(target_file, reference_files):
    """Save uploaded files (target-file mode)"""
    cleanup_temp()
    temp_dir = tempfile.mkdtemp()
    st.session_state.temp_dir = temp_dir
    
    # save target file
    target_path = Path(temp_dir) / target_file.name
    with open(target_path, 'wb') as f:
        f.write(target_file.getbuffer())
    
    # save reference files
    for ref_file in reference_files:
        ref_path = Path(temp_dir) / ref_file.name
        with open(ref_path, 'wb') as f:
            f.write(ref_file.getbuffer())
    
    return temp_dir


def save_all_files(uploaded_files):
    """Save all uploaded files (all-file mode)"""
    cleanup_temp()
    temp_dir = tempfile.mkdtemp()
    st.session_state.temp_dir = temp_dir
    
    for uploaded_file in uploaded_files:
        file_path = Path(temp_dir) / uploaded_file.name
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
    
    return temp_dir


def run_detection(submissions_dir, config_params):
    """Run the detection pipeline"""
    config = PipelineConfig(
        submissions_dir=Path(submissions_dir),
        output_dir=Path(submissions_dir),
        device=config_params['device'],
        use_parallel=config_params['use_parallel'],
        num_workers=config_params['num_workers'],
        similarity_threshold=config_params['threshold'],
        enable_paragraph_check=config_params['enable_paragraph'],
        enable_citation_check=config_params['enable_citation'],
        enable_multilingual=config_params['enable_multilingual'],
        para_threshold=config_params['para_threshold'],
    )
    
    pipeline = PlagiarismPipeline(config)
    
    with st.spinner('Analyzing text similarity...'):
        if config.enable_paragraph_check:
            sent_stats, sent_details, para_stats, para_details = pipeline.run_with_paragraphs()
            pipeline.write_reports(sent_stats, sent_details, para_stats, para_details)
            return {
                'sent_stats': sent_stats,
                'sent_details': sent_details,
                'para_stats': para_stats,
                'para_details': para_details,
            }
        else:
            stats, details = pipeline.run()
            pipeline.write_reports(stats, details)
            return {
                'sent_stats': stats,
                'sent_details': details,
                'para_stats': [],
                'para_details': [],
            }


def filter_results_by_target(results, target_filename):
    """Filter results to include only pairs containing the target file"""
    target_stem = Path(target_filename).stem
    
    filtered_stats = []
    filtered_details = []
    
    for i, stat in enumerate(results['sent_stats']):
        pair = stat['pair']
        if target_stem in pair:
            filtered_stats.append(stat)
            filtered_details.append(results['sent_details'][i])
    
    return {
        'sent_stats': filtered_stats,
        'sent_details': filtered_details,
        'para_stats': [],
        'para_details': [],
    }


def get_highlight_class(sim, penalty):
    """Choose highlight class based on similarity and citation penalty"""
    if penalty < 0.5:
        return "highlight-citation"
    elif sim >= 0.90:
        return "highlight-high"
    elif sim >= 0.80:
        return "highlight-medium"
    else:
        return "highlight-low"


def read_student_text(temp_dir, student_id):
    """Read raw text for a student/file from temp dir"""
    temp_path = Path(temp_dir)
    for file in temp_path.iterdir():
        if file.stem == student_id or file.name.startswith(student_id):
            return file.read_text(encoding='utf-8', errors='ignore')
    return ""


def normalize_pair(pair, target_id):
    """Normalize pair order so the target is always on the left"""
    if pair[0] == target_id:
        return pair[0], pair[1]
    else:
        return pair[1], pair[0]


def build_highlighted_text(student_id, text, detail, target_id):
    """Build HTML with highlighted matches"""
    if not text:
        return ""
    
    # Determine if this file is the target
    is_target = (student_id == target_id)
    
    # Split into paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    
    # Collect match info
    matches = []
    for hit in detail.get('hits', []):
        if is_target:
            # target file: find matches for it
            if hit['sid_i'] == student_id:
                matches.append({
                    'text': hit['text_i'],
                    'sent_id': hit['sent_id_i'],
                    'sim': hit.get('adjusted_sim', hit['sim']),
                    'penalty': hit.get('citation_penalty', 1.0),
                    'other_text': hit['text_j'],
                    'other_sid': hit['sid_j'],
                })
            elif hit['sid_j'] == student_id:
                matches.append({
                    'text': hit['text_j'],
                    'sent_id': hit['sent_id_j'],
                    'sim': hit.get('adjusted_sim', hit['sim']),
                    'penalty': hit.get('citation_penalty', 1.0),
                    'other_text': hit['text_i'],
                    'other_sid': hit['sid_i'],
                })
        else:
            # reference file: find its matches
            if hit['sid_j'] == student_id:
                matches.append({
                    'text': hit['text_j'],
                    'sent_id': hit['sent_id_j'],
                    'sim': hit.get('adjusted_sim', hit['sim']),
                    'penalty': hit.get('citation_penalty', 1.0),
                    'other_text': hit['text_i'],
                    'other_sid': hit['sid_i'],
                })
            elif hit['sid_i'] == student_id:
                matches.append({
                    'text': hit['text_i'],
                    'sent_id': hit['sent_id_i'],
                    'sim': hit.get('adjusted_sim', hit['sim']),
                    'penalty': hit.get('citation_penalty', 1.0),
                    'other_text': hit['text_j'],
                    'other_sid': hit['sid_j'],
                })
    
    # Build HTML
    html_parts = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        para_html = ""
        sentences = re.split(r'(?<=[。！？.!?;；])', para)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 5:
                continue
            
            # find matching info
            match_info = None
            for m in matches:
                if m['text'].strip() in sentence or sentence in m['text'].strip():
                    match_info = m
                    break
            
            if match_info:
                css_class = get_highlight_class(match_info['sim'], match_info['penalty'])
                tooltip = f"Similarity: {match_info['sim']:.1%}"
                if match_info['penalty'] < 1.0:
                    tooltip += f" (citation)"
                para_html += f'<span class="{css_class}" title="{tooltip}">{sentence}</span>'
            else:
                para_html += sentence
        
        html_parts.append(f"<p>{para_html}</p>")
    
    return "".join(html_parts)


def display_comparison_view(detail, temp_dir, target_id):
    """Display side-by-side comparison view"""
    pair = detail['pair']
    
    # Normalize: target on left, reference on right
    left_id, right_id = normalize_pair(pair, target_id)
    
    # Read texts
    text_left = read_student_text(temp_dir, left_id)
    text_right = read_student_text(temp_dir, right_id)
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Matching sentences", detail['count'])
    with col2:
        st.metric("Average similarity", f"{detail['mean_sim']:.1%}")
    with col3:
        st.metric("Text coverage", f"{detail.get('coverage_min', 0):.1%}")
    with col4:
        score = detail['score']
        if score >= 0.7:
            st.metric("Risk level", "⚠️ High", delta_color="off")
        elif score >= 0.5:
            st.metric("Risk level", "⚡ Medium", delta_color="off")
        else:
            st.metric("Risk level", "✓ Low", delta_color="off")
    
    st.divider()
    
    # Legend
    st.markdown("""
    <div style='margin-bottom: 20px;'>
        <div class="legend-item">
            <span class="legend-box" style="background-color: #ff6b6b;"></span>
            <span>High similarity (≥90%)</span>
        </div>
        <div class="legend-item">
            <span class="legend-box" style="background-color: #ffd93d;"></span>
            <span>Moderate similarity (80-90%)</span>
        </div>
        <div class="legend-item">
            <span class="legend-box" style="background-color: #a8e6cf;"></span>
            <span>Low similarity (&lt;80%)</span>
        </div>
        <div class="legend-item">
            <span class="legend-box" style="background-color: #d4a5ff; border: 1px dashed #9d4edd;"></span>
            <span>Possible citation</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Side-by-side display
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown(f'<div class="student-name">🎯 {left_id} (Target)</div>', unsafe_allow_html=True)
        highlighted_left = build_highlighted_text(left_id, text_left, detail, target_id)
        st.markdown(f'<div class="text-container target-file">{highlighted_left}</div>', unsafe_allow_html=True)
    
    with col_right:
        st.markdown(f'<div class="student-name">📚 {right_id} (Reference)</div>', unsafe_allow_html=True)
        highlighted_right = build_highlighted_text(right_id, text_right, detail, target_id)
        st.markdown(f'<div class="text-container reference-file">{highlighted_right}</div>', unsafe_allow_html=True)
    
    # Detailed match list
    with st.expander("📋 View detailed matches", expanded=False):
        for i, hit in enumerate(detail.get('hits', [])[:20], 1):
            sim = hit.get('adjusted_sim', hit['sim'])
            penalty = hit.get('citation_penalty', 1.0)
            
            # ensure left side is target
            if hit['sid_i'] == left_id:
                left_text = hit['text_i']
                left_sent = hit['sent_id_i']
                right_text = hit['text_j']
                right_sent = hit['sent_id_j']
            else:
                left_text = hit['text_j']
                left_sent = hit['sent_id_j']
                right_text = hit['text_i']
                right_sent = hit['sent_id_i']
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**{i}. {left_id}** (sentence {left_sent})")
                st.info(left_text)
            with col2:
                st.markdown(f"**{right_id}** (sentence {right_sent})")
                st.info(right_text)
            
            if penalty < 1.0:
                st.caption(f"✏️ Similarity: {sim:.1%} (detected citation, original: {hit['sim']:.1%})")
            else:
                st.caption(f"Similarity: {sim:.1%}")
            
            if i < len(detail.get('hits', [])[:20]):
                st.divider()


# Sidebar
with st.sidebar:
    st.header("⚙️ Detection Settings")
    
    device = st.selectbox("Compute device", ["Auto", "CPU", "GPU"])
    device_map = {"Auto": None, "CPU": "cpu", "GPU": "cuda"}
    
    use_parallel = st.checkbox("CPU multithreading", value=True)
    num_workers = st.slider("Threads", 1, 8, 2, disabled=not use_parallel)
    
    st.divider()
    
    threshold = st.slider("Sentence similarity threshold", 0.50, 0.95, 0.82, 0.01)
    enable_paragraph = st.checkbox("Paragraph check", value=True)
    para_threshold = st.slider("Paragraph threshold", 0.50, 0.90, 0.75, 0.01, disabled=not enable_paragraph)
    
    st.divider()
    
    enable_citation = st.checkbox("Citation detection", value=True)
    enable_multilingual = st.checkbox("Multilingual support", value=False)
    
    st.divider()
    
    if st.button("🗑️ Clear data"):
        cleanup_temp()
        st.session_state.results = None
        st.session_state.selected_pair = None
        st.session_state.target_file = None
        st.rerun()

# Main
st.title("🔍 Plagiarism Checker")

tab1, tab2 = st.tabs(["📁 File Upload", "📊 Comparison"])

with tab1:
    st.markdown("### Choose detection mode")
    
    mode = st.radio(
        "Detection mode",
        ["Target-file detection", "All-file comparison"],
        captions=[
            "Upload one target file and compare with multiple reference files",
            "Upload multiple files and compare all pairs"
        ],
        horizontal=True
    )
    
    st.divider()
    
    if mode == "Target-file detection":
        st.session_state.detection_mode = "target"
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎯 Target file")
            target_file = st.file_uploader(
                "Upload the target file",
                type=['txt', 'md'],
                key='target'
            )
            if target_file:
                st.success(f"✅ {target_file.name}")
                st.session_state.target_file = target_file.name
        
        with col2:
            st.markdown("#### 📚 Reference library")
            reference_files = st.file_uploader(
                "Upload reference files (multiple allowed)",
                type=['txt', 'md'],
                accept_multiple_files=True,
                key='references'
            )
            if reference_files:
                st.success(f"✅ {len(reference_files)} files selected")
                for rf in reference_files:
                    st.text(f"📄 {rf.name}")
        
        if target_file and reference_files:
            if st.button("🚀 Start Detection", type="primary", use_container_width=True):
                temp_dir = save_uploaded_files(target_file, reference_files)
                
                config_params = {
                    'device': device_map[device],
                    'use_parallel': use_parallel,
                    'num_workers': num_workers,
                    'threshold': threshold,
                    'para_threshold': para_threshold,
                    'enable_paragraph': enable_paragraph,
                    'enable_citation': enable_citation,
                    'enable_multilingual': enable_multilingual,
                }
                
                try:
                    results = run_detection(temp_dir, config_params)
                    # filter pairs that include the target file
                    filtered = filter_results_by_target(results, target_file.name)
                    st.session_state.results = filtered
                    if filtered['sent_stats']:
                        st.session_state.selected_pair = 0
                    st.success("✅ Detection complete! Switch to the 'Comparison' tab to view results")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Detection failed: {str(e)}")
        elif target_file or reference_files:
            st.warning("⚠️ Please upload both target and reference files")
    
    else:  # All-file comparison
        st.session_state.detection_mode = "all"
        st.session_state.target_file = None
        
        st.markdown("#### 📁 Upload all files")
        uploaded_files = st.file_uploader(
            "Supports .txt and .md formats. Multiple files allowed.",
            type=['txt', 'md'],
            accept_multiple_files=True,
            key='all_files'
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} files selected")
            cols = st.columns(3)
            for i, f in enumerate(uploaded_files):
                with cols[i % 3]:
                    st.text(f"📄 {f.name}")
        
        if uploaded_files and len(uploaded_files) >= 2:
            if st.button("🚀 Start Detection", type="primary", use_container_width=True):
                temp_dir = save_all_files(uploaded_files)
                
                config_params = {
                    'device': device_map[device],
                    'use_parallel': use_parallel,
                    'num_workers': num_workers,
                    'threshold': threshold,
                    'para_threshold': para_threshold,
                    'enable_paragraph': enable_paragraph,
                    'enable_citation': enable_citation,
                    'enable_multilingual': enable_multilingual,
                }
                
                try:
                    results = run_detection(temp_dir, config_params)
                    st.session_state.results = results
                    if results['sent_stats']:
                        st.session_state.selected_pair = 0
                    st.success("✅ Detection complete! Switch to the 'Comparison' tab to view results")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Detection failed: {str(e)}")
        elif uploaded_files:
            st.warning("⚠️ At least 2 files are required for comparison")

with tab2:
    if st.session_state.results and st.session_state.results['sent_stats']:
        results = st.session_state.results
        stats = results['sent_stats']
        details = results['sent_details']
        
        st.markdown("### Detection Results Overview")
        
        # build selector options
        pair_options = []
        for i, stat in enumerate(stats):
            pair = stat['pair']
            score = stat['score']
            risk = "🔴 High" if score >= 0.7 else "🟡 Medium" if score >= 0.5 else "🟢 Low"
            
            # adjust display per mode
            if st.session_state.detection_mode == "target" and st.session_state.target_file:
                target_stem = Path(st.session_state.target_file).stem
                other = pair[1] if pair[0] == target_stem else pair[0]
                pair_options.append(f"{target_stem} ⟷ {other} | Score: {score:.3f} | {risk}")
            else:
                pair_options.append(f"{pair[0]} ⟷ {pair[1]} | Score: {score:.3f} | {risk}")
        
        selected = st.selectbox(
            "Select a pair to view",
            range(len(pair_options)),
            format_func=lambda x: pair_options[x],
            key='pair_selector'
        )
        
        st.divider()
        
        # show comparison
        if selected is not None and st.session_state.temp_dir:
            detail = details[selected]
            
            # determine target id
            if st.session_state.detection_mode == "target" and st.session_state.target_file:
                target_id = Path(st.session_state.target_file).stem
            else:
                # all-file mode: default left is first
                target_id = detail['pair'][0]
            
            display_comparison_view(detail, st.session_state.temp_dir, target_id)
        
        # exports
        st.divider()
        st.markdown("### 📥 Export Reports")
        
        col1, col2 = st.columns(2)
        
        if st.session_state.temp_dir:
            temp_path = Path(st.session_state.temp_dir)
            
            with col1:
                csv_file = temp_path / "pair_summary.csv"
                if csv_file.exists():
                    st.download_button(
                        "📊 Download CSV summary",
                        csv_file.read_bytes(),
                        "pair_summary.csv",
                        "text/csv",
                        use_container_width=True
                    )
            
            with col2:
                json_file = temp_path / "pair_results.json"
                if json_file.exists():
                    st.download_button(
                        "📄 Download JSON details",
                        json_file.read_bytes(),
                        "pair_results.json",
                        "application/json",
                        use_container_width=True
                    )
    else:
        st.info("👈 Please upload files and start detection first")
        
        st.markdown("""
        ### 💡 Tips
        
        **Target-file detection**:
        - Upload one target file
        - Upload multiple reference files
        - The system checks whether the target file borrows from reference files
        - Good for checking student work against online sources
        
        **All-file comparison**:
        - Upload multiple files
        - The system compares similarity across all files
        - Good for batch checking student submissions against each other
        
        **Color legend**:
        - 🔴 Red: High similarity (≥90%)
        - 🟡 Yellow: Moderate similarity (80-90%)
        - 🟢 Green: Low similarity (<80%)
        - 🟣 Purple dashed: Possible citation
        
        Hover over highlighted text to see similarity percentage
        """)

st.divider()
st.caption("Plagiarism Checker v2.0 | Semantic similarity analysis powered by deep learning")

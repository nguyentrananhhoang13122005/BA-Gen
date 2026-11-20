import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  animateContainerEntrance,
  animateInspectorPanel,
  animateStaggerItems,
  animateSuccessFlash,
  useAnimatedNumber,
} from './animations.js';

const ISO_VI_MAP = {
  Performance: 'Hiệu năng & Tốc độ',
  Security: 'Bảo mật & An toàn',
  Usability: 'Dễ sử dụng & Trải nghiệm',
  Reliability: 'Độ ổn định & Tin cậy',
  Maintainability: 'Dễ bảo trì & Nâng cấp',
  Portability: 'Tương thích đa nền tảng',
};

const ISO_KEYS = Object.keys(ISO_VI_MAP);

const PIPELINE_STEPS = [
  '1. Đọc tài liệu & Tách câu yêu cầu',
  '2. Phân loại Tính năng (FR) & Chất lượng (NFR)',
  '3. Phát hiện từ mơ hồ & Viết lại câu rõ ràng',
  '4. Sinh kịch bản người dùng & Tình huống kiểm thử',
  '5. Vẽ sơ đồ chức năng tổng quan (Use Case)',
  '6. Đóng gói báo cáo đặc tả Word (.docx)',
];

function Icon({ name, size = 18 }) {
  const props = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: '1.9',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
  };

  switch (name) {
    case 'upload':
      return (
        <svg {...props}>
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      );
    case 'list':
      return (
        <svg {...props}>
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <line x1="7" y1="9" x2="17" y2="9" />
          <line x1="7" y1="13" x2="17" y2="13" />
          <line x1="7" y1="17" x2="13" y2="17" />
        </svg>
      );
    case 'users':
      return (
        <svg {...props}>
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case 'file':
      return (
        <svg {...props}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
      );
    case 'share':
      return (
        <svg {...props}>
          <circle cx="18" cy="5" r="3" />
          <circle cx="6" cy="12" r="3" />
          <circle cx="18" cy="19" r="3" />
          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
          <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
        </svg>
      );
    case 'sparkles':
      return (
        <svg {...props}>
          <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z" />
        </svg>
      );
    case 'check':
      return (
        <svg {...props}>
          <polyline points="20 6 9 17 4 12" />
        </svg>
      );
    case 'key':
      return (
        <svg {...props}>
          <circle cx="7.5" cy="15.5" r="5.5" />
          <path d="m21 2-9.6 9.6" />
          <path d="m15.5 7.5 3 3L22 7l-3-3" />
        </svg>
      );
    default:
      return (
        <svg {...props}>
          <rect x="3" y="3" width="18" height="18" rx="3" />
          <line x1="3" y1="9" x2="21" y2="9" />
          <line x1="9" y1="21" x2="9" y2="9" />
        </svg>
      );
  }
}

/**
 * Tô nổi bật các từ cảm tính/mơ hồ trong câu yêu cầu
 */
function HighlightedText({ text, vagueTerms = [] }) {
  if (!vagueTerms || vagueTerms.length === 0) {
    return <span>{text}</span>;
  }
  const sorted = [...vagueTerms].sort((a, b) => b.length - a.length);
  const escaped = sorted.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const regex = new RegExp(`(${escaped.join('|')})`, 'gi');
  const parts = text.split(regex);

  return (
    <span>
      {parts.map((part, idx) => {
        const isMatch = sorted.some((t) => t.toLowerCase() === part.toLowerCase());
        return isMatch ? (
          <span key={idx} className="vague-highlight" title="Từ viết chung chung, cần làm rõ">
            {part}
          </span>
        ) : (
          <span key={idx}>{part}</span>
        );
      })}
    </span>
  );
}

export default function App() {
  // Navigation view: 'setup' | 'requirements' | 'stories' | 'srs' | 'sync'
  const [activeView, setActiveView] = useState('setup');

  // AI Configuration state
  const [provider, setProvider] = useState('local_nlp');
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState('TF-IDF + LinearSVC (Bilingual NLP)');
  const [envDefaults, setEnvDefaults] = useState({});

  // Document Input state (Real user data only)
  const [projectName, setProjectName] = useState('');
  const [rawText, setRawText] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  // Analysis & Pipeline Animation state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeStepIdx, setActiveStepIdx] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [errorMsg, setErrorMsg] = useState('');
  const [result, setResult] = useState(null);

  // Master-Detail selection state for Requirements (Screen 2)
  const [reqFilter, setReqFilter] = useState('all');
  const [reqSearch, setReqSearch] = useState('');
  const [selectedReqId, setSelectedReqId] = useState(null);
  const [customSmartText, setCustomSmartText] = useState('');
  const [editType, setEditType] = useState('FR');
  const [editCategory, setEditCategory] = useState('Performance');
  const [isUpdatingReq, setIsUpdatingReq] = useState(false);

  // Master-Detail selection state for User Stories (Screen 3)
  const [selectedStoryId, setSelectedStoryId] = useState(null);

  // Sync Tab selection (Screen 5): 'rtm' | 'jira' | 'github' | 'trello'
  const [syncTab, setSyncTab] = useState('rtm');
  const [jiraForm, setJiraForm] = useState({ domain: '', email: '', token: '', project_key: 'PROJ' });
  const [ghForm, setGhForm] = useState({ repo: '', token: '' });
  const [trelloForm, setTrelloForm] = useState({ api_key: '', token: '', list_id: '' });
  const [syncStatus, setSyncStatus] = useState(null);

  // DOM Refs for JS Web Animations API
  const mainViewRef = useRef(null);
  const reqListRef = useRef(null);
  const reqInspectorRef = useRef(null);
  const storyListRef = useRef(null);
  const storyInspectorRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetch('/api/config-defaults')
      .then((r) => r.json())
      .then((d) => setEnvDefaults(d))
      .catch(() => {});
  }, []);

  // Update default model when provider changes
  const handleProviderChange = (newProv) => {
    setProvider(newProv);
    setErrorMsg('');
    if (newProv === 'local_nlp') setModelName('TF-IDF + LinearSVC (Bilingual NLP)');
    else if (newProv === 'groq') setModelName('llama-3.3-70b-versatile');
    else if (newProv === 'gemini') setModelName('gemini-1.5-flash');
    else if (newProv === 'openrouter') setModelName('meta-llama/llama-3.3-70b-instruct:free');
    else if (newProv === 'ollama') setModelName('llama3');
  };

  // Trigger JS entrance animation when switching views
  useEffect(() => {
    animateContainerEntrance(mainViewRef.current);
  }, [activeView]);

  // Live 60fps JS timer & step progression while analyzing
  useEffect(() => {
    if (!isAnalyzing) return;
    const start = performance.now();
    let rafId = null;

    const tick = (now) => {
      const diff = now - start;
      setElapsedMs(diff);
      const step = Math.min(Math.floor(diff / 750), 5);
      setActiveStepIdx(step);
      rafId = requestAnimationFrame(tick);
    };

    rafId = requestAnimationFrame(tick);
    return () => {
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [isAnalyzing]);

  // Derived metrics & animated numbers
  const totalReqs = result ? result.requirements.length : 0;
  const frCount = result ? result.requirements.filter((r) => r.req_type === 'FR').length : 0;
  const nfrCount = result ? result.requirements.filter((r) => r.req_type === 'NFR').length : 0;
  const ambiguousCount = result ? result.requirements.filter((r) => r.is_ambiguous).length : 0;
  const clarityPct = totalReqs > 0 ? Math.round(((totalReqs - ambiguousCount) / totalReqs) * 100) : 0;

  const animTotal = useAnimatedNumber(totalReqs);
  const animFr = useAnimatedNumber(frCount);
  const animNfr = useAnimatedNumber(nfrCount);
  const animClarity = useAnimatedNumber(clarityPct);

  // Filtered requirements
  const filteredRequirements = useMemo(() => {
    if (!result) return [];
    return result.requirements.filter((r) => {
      if (reqFilter === 'ambiguous' && !r.is_ambiguous) return false;
      if (reqFilter === 'clean' && r.is_ambiguous) return false;
      if (reqFilter === 'FR' && r.req_type !== 'FR') return false;
      if (reqFilter === 'NFR' && r.req_type !== 'NFR') return false;
      if (reqSearch.trim()) {
        const q = reqSearch.trim().toLowerCase();
        if (!r.req_id.toLowerCase().includes(q) && !r.raw_text.toLowerCase().includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [result, reqFilter, reqSearch]);

  // Keep selectedReqId synced
  const selectedReq = useMemo(() => {
    if (!result || !result.requirements.length) return null;
    return (
      result.requirements.find((r) => r.req_id === selectedReqId) ||
      filteredRequirements[0] ||
      result.requirements[0]
    );
  }, [result, selectedReqId, filteredRequirements]);

  useEffect(() => {
    if (selectedReq) {
      setCustomSmartText(selectedReq.smart_rewrite || selectedReq.raw_text);
      setEditType(selectedReq.req_type);
      setEditCategory(selectedReq.nfr_category || 'Performance');
      animateInspectorPanel(reqInspectorRef.current);
    }
  }, [selectedReq?.req_id]);

  useEffect(() => {
    if (activeView === 'requirements') {
      animateStaggerItems(reqListRef.current);
    } else if (activeView === 'stories') {
      animateStaggerItems(storyListRef.current);
    }
  }, [activeView, reqFilter]);

  const selectedStory = useMemo(() => {
    if (!result || !result.user_stories.length) return null;
    return (
      result.user_stories.find((u) => u.story_id === selectedStoryId) || result.user_stories[0]
    );
  }, [result, selectedStoryId]);

  useEffect(() => {
    if (selectedStory) {
      animateInspectorPanel(storyInspectorRef.current);
    }
  }, [selectedStory?.story_id]);

  const hasValidKey =
    provider === 'local_nlp' ||
    provider === 'ollama' ||
    apiKey.trim().length >= 8 ||
    (provider === 'groq' && envDefaults.has_env_groq) ||
    (provider === 'gemini' && envDefaults.has_env_gemini) ||
    (provider === 'openrouter' && envDefaults.has_env_openrouter);

  // Execute real AI Analysis
  const handleRunAnalysis = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!hasValidKey) {
      setErrorMsg('Vui lòng nhập API Key thực tế ở khung Kết nối AI bên trái trước khi phân tích.');
      return;
    }

    if (!selectedFile && !rawText.trim()) {
      setErrorMsg('Vui lòng tải lên tệp tài liệu (.docx / .txt) hoặc dán nội dung yêu cầu cần phân tích.');
      return;
    }

    setIsAnalyzing(true);
    setActiveStepIdx(0);

    try {
      const formData = new FormData();
      formData.append('provider', provider);
      formData.append('api_key', apiKey.trim());
      formData.append('model_name', modelName.trim());
      formData.append('project_name', projectName.trim());
      formData.append('raw_text', rawText);
      if (selectedFile) {
        formData.append('file', selectedFile);
      }

      const resp = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Lỗi khi phân tích tài liệu qua AI API.');
      }

      setResult(data);
      if (data.requirements?.length > 0) {
        setSelectedReqId(data.requirements[0].req_id);
      }
      if (data.user_stories?.length > 0) {
        setSelectedStoryId(data.user_stories[0].story_id);
      }
      setActiveView('requirements');
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Apply SMART rewrite for 1 requirement
  const handleApplySmartSingle = async (reqId) => {
    setIsUpdatingReq(true);
    try {
      const resp = await fetch(`/api/requirements/${reqId}/apply-smart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_text: customSmartText }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setResult(data);
        animateSuccessFlash(reqInspectorRef.current);
      }
    } finally {
      setIsUpdatingReq(false);
    }
  };

  // Apply SMART rewrite for ALL ambiguous requirements
  const handleApplySmartAll = async () => {
    setIsUpdatingReq(true);
    try {
      const resp = await fetch('/api/requirements/apply-smart-all', { method: 'POST' });
      const data = await resp.json();
      if (resp.ok) {
        setResult(data);
        animateSuccessFlash(reqInspectorRef.current);
      }
    } finally {
      setIsUpdatingReq(false);
    }
  };

  // Update FR/NFR classification
  const handleUpdateType = async (reqId) => {
    setIsUpdatingReq(true);
    try {
      const resp = await fetch(`/api/requirements/${reqId}/update-type`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          req_type: editType,
          nfr_category: editType === 'NFR' ? editCategory : null,
        }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setResult(data);
        animateSuccessFlash(reqInspectorRef.current);
      }
    } finally {
      setIsUpdatingReq(false);
    }
  };

  // Sync handlers for Jira / GitHub / Trello
  const handleSyncApi = async (platform) => {
    setSyncStatus({ loading: true, msg: 'Đang đồng bộ dữ liệu...', isError: false });
    try {
      let url = '';
      let payload = {};
      if (platform === 'jira') {
        url = '/api/sync/jira';
        payload = jiraForm;
      } else if (platform === 'github') {
        url = '/api/sync/github';
        payload = ghForm;
      } else {
        url = '/api/sync/trello';
        payload = trelloForm;
      }

      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Lỗi kết nối API');
      }
      if (data.errors && data.errors.length > 0) {
        setSyncStatus({
          loading: false,
          msg: `Thành công ${data.success_count}, lỗi ${data.errors.length}: ${data.errors[0].error}`,
          isError: true,
        });
      } else {
        setSyncStatus({
          loading: false,
          msg: `Đã đồng bộ thành công ${data.success_count} mục lên ${platform.toUpperCase()}!`,
          isError: false,
        });
      }
    } catch (err) {
      setSyncStatus({ loading: false, msg: err.message, isError: true });
    }
  };

  const viewTitles = {
    setup: {
      title: 'Thiết lập Kết nối AI & Đưa Tài liệu Dự án vào',
      sub: 'Tải lên file Word (.docx), file văn bản (.txt) hoặc dán nội dung yêu cầu thực tế để AI bóc tách',
    },
    requirements: {
      title: '1. Danh sách Yêu cầu & Chỉnh sửa Câu mơ hồ (Chuẩn SMART)',
      sub: 'Chọn một câu yêu cầu ở cột bên trái để xem phân tích chi tiết và áp dụng câu viết lại ở cột bên phải',
    },
    stories: {
      title: '2. Kịch bản Người dùng (User Stories) & Tình huống Kiểm thử',
      sub: 'Chọn một kịch bản ở cột bên trái để xem chi tiết Ai dùng - Muốn làm gì - Lợi ích gì và các bước kiểm thử',
    },
    srs: {
      title: '3. Sơ đồ Chức năng (Use Case) & Xuất Báo cáo Đặc tả Word (.docx)',
      sub: 'Xem trực tiếp sơ đồ tổng quan hệ thống và tải tài liệu đặc tả phần mềm 6 chương hoàn chỉnh',
    },
    sync: {
      title: '4. Ma trận Truy vết Yêu cầu & Đồng bộ Jira / GitHub / Trello',
      sub: 'Kiểm tra bảng ánh xạ yêu cầu 2 chiều và xuất dữ liệu sang các công cụ quản lý dự án',
    },
  };

  return (
    <div className="app-shell">
      {/* ====================================================================
          LEFT NAVIGATION SIDEBAR (CLEAN & FOCUSED)
          ==================================================================== */}
      <aside className="app-sidebar">
        <div className="sidebar-top">
          <div className="brand-box">
            <div className="brand-logo">
              <Icon name="blueprint" size={20} />
            </div>
            <div>
              <div className="brand-title">BA-Gen Studio</div>
              <div className="brand-sub">React · AI Requirements Assistant</div>
            </div>
          </div>

          <div className="nav-section-label">Không gian làm việc</div>
          <div className="nav-list">
            <button
              type="button"
              className={`nav-btn ${activeView === 'setup' ? 'is-active' : ''}`}
              onClick={() => setActiveView('setup')}
            >
              <span className="nav-btn-left">
                <Icon name="upload" size={17} />
                <span>Tài liệu &amp; Kết nối AI</span>
              </span>
            </button>

            <button
              type="button"
              disabled={!result}
              className={`nav-btn ${activeView === 'requirements' ? 'is-active' : ''}`}
              onClick={() => setActiveView('requirements')}
            >
              <span className="nav-btn-left">
                <Icon name="list" size={17} />
                <span>1. Yêu cầu &amp; Sửa mơ hồ</span>
              </span>
              {result && <span className="nav-count-pill">{totalReqs}</span>}
            </button>

            <button
              type="button"
              disabled={!result}
              className={`nav-btn ${activeView === 'stories' ? 'is-active' : ''}`}
              onClick={() => setActiveView('stories')}
            >
              <span className="nav-btn-left">
                <Icon name="users" size={17} />
                <span>2. Kịch bản Người dùng</span>
              </span>
              {result && <span className="nav-count-pill">{result.user_stories.length}</span>}
            </button>

            <button
              type="button"
              disabled={!result}
              className={`nav-btn ${activeView === 'srs' ? 'is-active' : ''}`}
              onClick={() => setActiveView('srs')}
            >
              <span className="nav-btn-left">
                <Icon name="file" size={17} />
                <span>3. Sơ đồ &amp; File Word</span>
              </span>
            </button>

            <button
              type="button"
              disabled={!result}
              className={`nav-btn ${activeView === 'sync' ? 'is-active' : ''}`}
              onClick={() => setActiveView('sync')}
            >
              <span className="nav-btn-left">
                <Icon name="share" size={17} />
                <span>4. Đồng bộ &amp; Truy vết</span>
              </span>
            </button>
          </div>
        </div>

        <div className="sidebar-bottom">
          <div className="ai-status-card">
            <div className="ai-status-row">
              <span className={`status-dot ${hasValidKey ? 'online' : 'missing'}`} />
              <span>
                {hasValidKey
                  ? `Đã kết nối: ${provider.toUpperCase()}`
                  : 'Chưa nhập API Key'}
              </span>
            </div>
            <div style={{ color: '#94A3B8', fontSize: '0.73rem' }}>
              {result
                ? `Dự án: ${result.project.project_name}`
                : 'Chọn mục "Tài liệu & Kết nối AI" để thiết lập'}
            </div>
          </div>
        </div>
      </aside>

      {/* ====================================================================
          MAIN WORKSPACE AREA
          ==================================================================== */}
      <div className="app-main">
        {/* TOP HEADER BAR WITH ANIMATED JS METRICS */}
        <header className="topbar">
          <div>
            <div className="topbar-title">{viewTitles[activeView].title}</div>
            <div className="topbar-sub">{viewTitles[activeView].sub}</div>
          </div>

          {result && (
            <div className="topbar-metrics">
              <div className="metric-chip">
                <span>Tổng:</span>
                <strong>{animTotal} câu</strong>
              </div>
              <div className="metric-chip" style={{ color: '#0F766E' }}>
                <span>Tính năng:</span>
                <strong>{animFr}</strong>
              </div>
              <div className="metric-chip" style={{ color: '#1D4ED8' }}>
                <span>Chất lượng:</span>
                <strong>{animNfr}</strong>
              </div>
              <div className="metric-chip" style={{ color: clarityPct >= 80 ? '#15803D' : '#B45309' }}>
                <span>Độ rõ ràng:</span>
                <strong>{animClarity}%</strong>
              </div>
              <a href="/api/export/srs-docx" className="btn btn-primary" style={{ padding: '7px 13px', fontSize: '0.82rem' }}>
                <Icon name="file" size={15} />
                <span>Tải File Word (.docx)</span>
              </a>
            </div>
          )}
        </header>

        {/* FOCUSED SINGLE-SCREEN WORKSPACE */}
        <main className="workspace-body" ref={mainViewRef}>
          {/* ================================================================
              SCREEN 1: SETUP AI & UPLOAD REAL DOCUMENT
              ================================================================ */}
          {activeView === 'setup' && (
            <form className="setup-grid" onSubmit={handleRunAnalysis}>
              {/* LEFT CARD: AI CONNECTION */}
              <div className="panel-card">
                <div className="panel-header">
                  <div className="panel-title-group">
                    <div className="panel-icon">
                      <Icon name="key" size={18} />
                    </div>
                    <div>
                      <div className="panel-title">1. Kết nối Mô hình AI</div>
                      <div className="panel-subtitle">Nhập khóa API để phân tích dữ liệu thật</div>
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Chọn Bộ máy Xử lý Ngôn ngữ &amp; AI</label>
                  <select
                    className="form-select"
                    value={provider}
                    onChange={(e) => handleProviderChange(e.target.value)}
                  >
                    <option value="local_nlp">
                      Mô hình NLP &amp; Học máy Tích hợp trên máy (Chạy ngay - Không cần API Key)
                    </option>
                    <option value="groq">Groq Cloud AI (Llama 3.3 70B - Cần nhập API Key)</option>
                    <option value="gemini">Google Gemini AI (Gemini 1.5 Flash - Cần nhập API Key)</option>
                    <option value="openrouter">OpenRouter AI (Đa mô hình - Cần nhập API Key)</option>
                    <option value="ollama">Ollama Local Server (localhost:11434)</option>
                  </select>
                </div>

                {provider !== 'ollama' && provider !== 'local_nlp' && (
                  <div className="form-group">
                    <label className="form-label">
                      Mã khóa API Key ({provider.toUpperCase()})
                    </label>
                    <input
                      type="password"
                      className="form-input"
                      placeholder={
                        provider === 'groq'
                          ? 'Dán khóa gsk_... vào đây'
                          : provider === 'gemini'
                          ? 'Dán khóa AIza... vào đây'
                          : 'Dán khóa sk-or-... vào đây'
                      }
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                    />
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Mô hình xử lý</label>
                  <input
                    type="text"
                    className="form-input"
                    value={modelName}
                    disabled={provider === 'local_nlp'}
                    onChange={(e) => setModelName(e.target.value)}
                  />
                </div>

                <div
                  style={{
                    padding: '12px 14px',
                    borderRadius: '8px',
                    fontSize: '0.83rem',
                    background: hasValidKey ? '#F0FDF4' : '#FFFBEB',
                    border: `1px solid ${hasValidKey ? '#86EFAC' : '#FCD34D'}`,
                    color: hasValidKey ? '#166534' : '#92400E',
                  }}
                >
                  {provider === 'local_nlp' ? (
                    <>
                      <strong>Sẵn sàng chạy trực tiếp trên máy:</strong> Sử dụng thuật toán tách câu NLP song ngữ và mô hình học máy <code>scikit-learn LinearSVC</code> để phân tích trực tiếp file <code>.docx / .txt</code> bạn tải lên mà không cần API Key.
                    </>
                  ) : provider === 'ollama' && !envDefaults.ollama_running ? (
                    <>
                      <strong>Lưu ý Ollama (cổng 11434):</strong> Máy hiện chưa bật dịch vụ Ollama ở cổng 11434, hệ thống sẽ tự động chuyển sang <strong>Mô hình NLP &amp; Học máy Tích hợp trên máy</strong> để phân tích tài liệu của bạn mà không bị lỗi kết nối.
                    </>
                  ) : hasValidKey ? (
                    <>
                      <strong>Đã sẵn sàng kết nối AI ({provider.toUpperCase()}):</strong> Bạn có thể tải tài liệu thực tế ở khung bên phải và bắt đầu phân tích.
                    </>
                  ) : (
                    <>
                      <strong>Chưa có API Key:</strong> Vui lòng dán API Key vào ô trên, hoặc chuyển sang <em>"Mô hình NLP &amp; Học máy Tích hợp trên máy"</em> nếu muốn chạy trực tiếp không cần Key.
                    </>
                  )}
                </div>
              </div>

              {/* RIGHT CARD: REAL DOCUMENT UPLOAD & INPUT */}
              <div className="panel-card">
                <div className="panel-header">
                  <div className="panel-title-group">
                    <div className="panel-icon">
                      <Icon name="upload" size={18} />
                    </div>
                    <div>
                      <div className="panel-title">2. Tài liệu Yêu cầu Thực tế của Dự án</div>
                      <div className="panel-subtitle">
                        Hỗ trợ tải tệp Microsoft Word (.docx), tệp văn bản (.txt) hoặc dán trực tiếp
                      </div>
                    </div>
                  </div>
                </div>

                {errorMsg && (
                  <div
                    style={{
                      background: '#FEF2F2',
                      border: '1px solid #FCA5A5',
                      color: '#B91C1C',
                      padding: '12px 14px',
                      borderRadius: '8px',
                      fontSize: '0.88rem',
                      marginBottom: '16px',
                      fontWeight: 500,
                    }}
                  >
                    {errorMsg}
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Tên Dự án / Hệ thống phần mềm</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Nhập tên dự án của bạn (hoặc để trống để lấy tự động theo tên file)..."
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Tải lên file tài liệu (.docx hoặc .txt)</label>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".docx,.txt"
                    style={{ display: 'none' }}
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  />
                  <div
                    className={`dropzone ${selectedFile ? 'has-file' : ''}`}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <div style={{ fontWeight: 600, color: '#1E3A8A', marginBottom: '4px' }}>
                      {selectedFile
                        ? `Đã chọn tệp: ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)`
                        : 'Nhấn vào đây để chọn tệp tài liệu (.docx, .txt) từ máy tính'}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#64748B' }}>
                      {selectedFile
                        ? 'Nhấn để đổi tệp khác'
                        : 'Đọc được cả đoạn văn và bảng biểu trong file Word (.docx)'}
                    </div>
                  </div>
                  {selectedFile && (
                    <button
                      type="button"
                      className="btn btn-outline"
                      style={{ padding: '5px 10px', fontSize: '0.78rem', marginBottom: '8px' }}
                      onClick={() => setSelectedFile(null)}
                    >
                      Gỡ tệp đã chọn
                    </button>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label">
                    Hoặc dán trực tiếp nội dung mô tả yêu cầu phần mềm vào đây:
                  </label>
                  <textarea
                    className="form-textarea"
                    placeholder="Dán nội dung mô tả bài toán, biên bản khảo sát khách hàng hoặc danh sách yêu cầu của bạn vào đây..."
                    value={rawText}
                    onChange={(e) => setRawText(e.target.value)}
                  />
                  <div style={{ fontSize: '0.78rem', color: '#64748B', marginTop: '4px' }}>
                    Độ dài hiện tại: {rawText.trim().length} ký tự
                  </div>
                </div>

                <button type="submit" className="btn btn-primary btn-full" disabled={isAnalyzing}>
                  <Icon name="sparkles" size={18} />
                  <span>Bắt đầu Phân tích Tài liệu Thực tế với AI</span>
                </button>
              </div>
            </form>
          )}

          {/* ================================================================
              SCREEN 2: REQUIREMENTS & SMART REFINEMENT (MASTER-DETAIL)
              ================================================================ */}
          {activeView === 'requirements' && result && (
            <div>
              {/* FILTER & BATCH ACTION TOOLBAR */}
              <div className="toolbar-row">
                <div className="filter-pills">
                  {[
                    { id: 'all', label: `Tất cả (${totalReqs})` },
                    { id: 'ambiguous', label: `Cần làm rõ (${ambiguousCount})` },
                    { id: 'clean', label: `Đã rõ ràng (${totalReqs - ambiguousCount})` },
                    { id: 'FR', label: `Tính năng (${frCount})` },
                    { id: 'NFR', label: `Chất lượng (${nfrCount})` },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      type="button"
                      className={`pill-btn ${reqFilter === tab.id ? 'active' : ''}`}
                      onClick={() => setReqFilter(tab.id)}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  <input
                    type="text"
                    className="form-input"
                    style={{ width: '240px', padding: '7px 12px', fontSize: '0.84rem' }}
                    placeholder="Tìm theo mã REQ hoặc từ khóa..."
                    value={reqSearch}
                    onChange={(e) => setReqSearch(e.target.value)}
                  />
                  {ambiguousCount > 0 && (
                    <button
                      type="button"
                      className="btn btn-success"
                      style={{ padding: '7px 13px', fontSize: '0.82rem' }}
                      disabled={isUpdatingReq}
                      onClick={handleApplySmartAll}
                    >
                      <Icon name="sparkles" size={15} />
                      <span>Áp dụng gợi ý cho tất cả ({ambiguousCount} câu)</span>
                    </button>
                  )}
                </div>
              </div>

              {/* MASTER-DETAIL SPLIT GRID */}
              <div className="master-detail-grid">
                {/* LEFT PANE: SCANNABLE REQUIREMENT LIST */}
                <div className="master-list" ref={reqListRef}>
                  {filteredRequirements.map((req) => (
                    <div
                      key={req.req_id}
                      className={`list-item-card js-stagger-item ${
                        selectedReq?.req_id === req.req_id ? 'selected' : ''
                      }`}
                      onClick={() => setSelectedReqId(req.req_id)}
                    >
                      <div className="list-item-top">
                        <div className="list-item-badges">
                          <span className="badge badge-id">{req.req_id}</span>
                          <span className={`badge ${req.req_type === 'FR' ? 'badge-fr' : 'badge-nfr'}`}>
                            {req.req_type === 'FR' ? 'Tính năng (FR)' : 'Chất lượng (NFR)'}
                          </span>
                          {req.nfr_category && (
                            <span className="badge badge-neutral">
                              {ISO_VI_MAP[req.nfr_category] || req.nfr_category}
                            </span>
                          )}
                        </div>
                        <span className={`badge ${req.is_ambiguous ? 'badge-warn' : 'badge-ok'}`}>
                          {req.is_ambiguous ? 'Cần làm rõ' : 'Đã rõ ràng'}
                        </span>
                      </div>
                      <div className="list-item-text">
                        <HighlightedText text={req.raw_text} vagueTerms={req.vague_terms} />
                      </div>
                    </div>
                  ))}
                  {filteredRequirements.length === 0 && (
                    <div className="panel-card" style={{ textAlign: 'center', color: '#64748B' }}>
                      Không có câu yêu cầu nào khớp với bộ lọc hiện tại.
                    </div>
                  )}
                </div>

                {/* RIGHT PANE: FOCUSED INSPECTOR FOR SELECTED REQUIREMENT */}
                {selectedReq && (
                  <div className="detail-inspector" ref={reqInspectorRef}>
                    <div className="panel-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span className="badge badge-id" style={{ fontSize: '0.85rem', padding: '4px 10px' }}>
                          {selectedReq.req_id}
                        </span>
                        <span
                          className={`badge ${selectedReq.req_type === 'FR' ? 'badge-fr' : 'badge-nfr'}`}
                        >
                          {selectedReq.req_type === 'FR'
                            ? 'Tính năng hệ thống (Chức năng)'
                            : 'Yêu cầu Chất lượng (Phi chức năng)'}
                        </span>
                        <span className="badge badge-neutral">
                          Độ tin cậy: {Math.round(selectedReq.confidence * 100)}%
                        </span>
                      </div>
                      <span className={`badge ${selectedReq.is_ambiguous ? 'badge-warn' : 'badge-ok'}`}>
                        {selectedReq.is_ambiguous ? 'Cần làm rõ thêm' : 'Đã viết rõ ràng'}
                      </span>
                    </div>

                    {/* ORIGINAL REQUIREMENT */}
                    <div className="compare-box original">
                      <div className="compare-label" style={{ color: '#475569' }}>
                        Nội dung yêu cầu hiện tại
                      </div>
                      <div>
                        <HighlightedText
                          text={selectedReq.raw_text}
                          vagueTerms={selectedReq.vague_terms}
                        />
                      </div>
                    </div>

                    {/* WHY IT NEEDS CLARIFICATION */}
                    {selectedReq.is_ambiguous && (
                      <div className="compare-box warning">
                        <div className="compare-label">Vì sao câu này cần làm rõ thêm?</div>
                        <ul style={{ paddingLeft: '18px', fontSize: '0.86rem' }}>
                          {selectedReq.vague_terms?.length > 0 && (
                            <li>
                              Chứa từ mang tính cảm tính: <strong>{selectedReq.vague_terms.join(', ')}</strong> (nên thay bằng con số đo lường cụ thể).
                            </li>
                          )}
                          {selectedReq.missing_actor && (
                            <li>Chưa nêu rõ ai là người sử dụng hoặc thực hiện chức năng này.</li>
                          )}
                          {selectedReq.missing_metric && (
                            <li>Yêu cầu về chất lượng nhưng chưa có ngưỡng đo lường cụ thể (thời gian, tỷ lệ %...).</li>
                          )}
                        </ul>
                      </div>
                    )}

                    {/* SMART REWRITE SUGGESTION & INLINE EDITOR */}
                    <div className="compare-box smart">
                      <div className="compare-label">
                        <Icon name="sparkles" size={15} />
                        <span>Gợi ý viết lại rõ ràng &amp; đầy đủ thông số (Chuẩn SMART)</span>
                      </div>
                      <textarea
                        className="form-textarea"
                        style={{
                          minHeight: '90px',
                          marginTop: '6px',
                          background: '#FFFFFF',
                          fontSize: '0.88rem',
                        }}
                        value={customSmartText}
                        onChange={(e) => setCustomSmartText(e.target.value)}
                      />
                      <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
                        <button
                          type="button"
                          className="btn btn-success"
                          disabled={isUpdatingReq}
                          onClick={() => handleApplySmartSingle(selectedReq.req_id)}
                        >
                          <Icon name="check" size={16} />
                          <span>Áp dụng câu viết lại này cho {selectedReq.req_id}</span>
                        </button>
                      </div>
                    </div>

                    {/* MANUAL CLASSIFICATION EDITOR */}
                    <div
                      style={{
                        borderTop: '1px solid #E2E8F0',
                        paddingTop: '14px',
                        marginTop: '14px',
                      }}
                    >
                      <div className="form-label" style={{ marginBottom: '8px' }}>
                        Đổi phân loại yêu cầu thủ công (nếu cần):
                      </div>
                      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                        <select
                          className="form-select"
                          style={{ flex: '1', minWidth: '150px' }}
                          value={editType}
                          onChange={(e) => setEditType(e.target.value)}
                        >
                          <option value="FR">Tính năng hệ thống (FR)</option>
                          <option value="NFR">Yêu cầu chất lượng (NFR)</option>
                        </select>

                        {editType === 'NFR' && (
                          <select
                            className="form-select"
                            style={{ flex: '1.3', minWidth: '180px' }}
                            value={editCategory}
                            onChange={(e) => setEditCategory(e.target.value)}
                          >
                            {ISO_KEYS.map((k) => (
                              <option key={k} value={k}>
                                {ISO_VI_MAP[k]} ({k})
                              </option>
                            ))}
                          </select>
                        )}

                        <button
                          type="button"
                          className="btn btn-outline"
                          disabled={isUpdatingReq}
                          onClick={() => handleUpdateType(selectedReq.req_id)}
                        >
                          Lưu phân loại
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ================================================================
              SCREEN 3: USER STORIES & TEST SCENARIOS (MASTER-DETAIL)
              ================================================================ */}
          {activeView === 'stories' && result && (
            <div className="master-detail-grid">
              {/* LEFT PANE: USER STORIES LIST */}
              <div className="master-list" ref={storyListRef}>
                {result.user_stories.map((us) => (
                  <div
                    key={us.story_id}
                    className={`list-item-card js-stagger-item ${
                      selectedStory?.story_id === us.story_id ? 'selected' : ''
                    }`}
                    onClick={() => setSelectedStoryId(us.story_id)}
                  >
                    <div className="list-item-top">
                      <div className="list-item-badges">
                        <span className="badge badge-id">{us.story_id}</span>
                        <span className="badge badge-fr">Từ: {us.req_id}</span>
                        <span className="badge badge-neutral">Người dùng: {us.role}</span>
                      </div>
                      <span className="badge badge-ok">
                        {us.acceptance_criteria.length} kịch bản kiểm thử
                      </span>
                    </div>
                    <div className="list-item-text" style={{ fontWeight: 600 }}>
                      {us.puml_usecase_name}
                    </div>
                    <div style={{ fontSize: '0.84rem', color: '#475569', marginTop: '3px' }}>
                      Là một <strong>{us.role}</strong>, tôi muốn {us.goal}
                    </div>
                  </div>
                ))}
              </div>

              {/* RIGHT PANE: SELECTED STORY & GHERKIN TEST SCENARIOS */}
              {selectedStory && (
                <div className="detail-inspector" ref={storyInspectorRef}>
                  <div className="panel-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span className="badge badge-id" style={{ fontSize: '0.85rem', padding: '4px 10px' }}>
                        {selectedStory.story_id}
                      </span>
                      <span className="badge badge-fr">Truy vết từ: {selectedStory.req_id}</span>
                      <span className="badge badge-neutral">
                        Chức năng: {selectedStory.puml_usecase_name}
                      </span>
                    </div>
                  </div>

                  <div className="story-3grid">
                    <div className="story-cell">
                      <div className="story-cell-label">1. Ai là người sử dụng?</div>
                      <div className="story-cell-val">{selectedStory.role}</div>
                    </div>
                    <div className="story-cell">
                      <div className="story-cell-label">2. Họ muốn làm việc gì?</div>
                      <div className="story-cell-val">{selectedStory.goal}</div>
                    </div>
                    <div className="story-cell">
                      <div className="story-cell-label">3. Để đạt lợi ích gì?</div>
                      <div className="story-cell-val">{selectedStory.benefit}</div>
                    </div>
                  </div>

                  <div className="form-label" style={{ marginBottom: '10px' }}>
                    Các tình huống kiểm thử nghiệm thu (Làm sao biết tính năng đã chạy đúng?):
                  </div>

                  {selectedStory.acceptance_criteria.map((ac, idx) => (
                    <div key={idx} className="scenario-card">
                      <div className="scenario-title">
                        Tình huống {idx + 1}: {ac.scenario}
                      </div>
                      <div className="step-row">
                        <span className="step-tag given">• Bối cảnh đầu:</span>
                        <span>{ac.given}</span>
                      </div>
                      <div className="step-row">
                        <span className="step-tag when">• Khi thao tác:</span>
                        <span>{ac.when}</span>
                      </div>
                      <div className="step-row">
                        <span className="step-tag then">• Kết quả đạt:</span>
                        <span>{ac.then}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ================================================================
              SCREEN 4: USE CASE DIAGRAM & SRS WORD EXPORT
              ================================================================ */}
          {activeView === 'srs' && result && (
            <div className="master-detail-grid">
              {/* LEFT: USE CASE DIAGRAM */}
              <div className="panel-card">
                <div className="panel-header">
                  <div className="panel-title-group">
                    <div className="panel-icon">
                      <Icon name="share" size={18} />
                    </div>
                    <div>
                      <div className="panel-title">Sơ đồ Chức năng Tổng quan (Use Case Diagram)</div>
                      <div className="panel-subtitle">
                        Minh họa các tác nhân và chức năng rút trích từ tài liệu của bạn
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {result.has_diagram_image && (
                      <a
                        href="/api/export/diagram-png"
                        download={`${result.project.project_name}_usecase.png`}
                        className="btn btn-primary"
                        style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                      >
                        Tải Ảnh (.png)
                      </a>
                    )}
                    <a
                      href="/api/export/diagram-puml"
                      download={`${result.project.project_name}_usecase.puml`}
                      className="btn btn-outline"
                      style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                    >
                      Tải Mã (.puml)
                    </a>
                  </div>
                </div>

                {result.has_diagram_image ? (
                  <div style={{ textAlign: 'center', background: '#F8FAFC', padding: '16px', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                    <img
                      src={`/api/export/diagram-png?t=${Date.now()}`}
                      alt="Use Case Diagram"
                      style={{ maxWidth: '100%', height: 'auto', borderRadius: '6px' }}
                    />
                  </div>
                ) : (
                  <div style={{ color: '#64748B', fontSize: '0.88rem', marginBottom: '12px' }}>
                    Mã nguồn vẽ sơ đồ PlantUML đã được khởi tạo bên dưới:
                  </div>
                )}

                <div style={{ marginTop: '14px' }}>
                  <div className="form-label">Mã nguồn kỹ thuật PlantUML:</div>
                  <pre
                    style={{
                      background: '#0F172A',
                      color: '#E2E8F0',
                      padding: '12px',
                      borderRadius: '8px',
                      fontSize: '0.78rem',
                      fontFamily: 'var(--font-mono)',
                      overflowX: 'auto',
                      maxHeight: '220px',
                    }}
                  >
                    {result.plantuml_code}
                  </pre>
                </div>
              </div>

              {/* RIGHT: SRS DOCUMENT EXPORT & PREVIEW */}
              <div className="panel-card">
                <div className="panel-header">
                  <div className="panel-title-group">
                    <div className="panel-icon">
                      <Icon name="file" size={18} />
                    </div>
                    <div>
                      <div className="panel-title">Báo cáo Đặc tả Phần mềm (SRS - 6 Chương)</div>
                      <div className="panel-subtitle">
                        Đóng gói chuẩn IEEE 830 / ISO 29148 sẵn sàng tải về nộp hoặc gửi khách hàng
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <a
                      href="/api/export/srs-docx"
                      className="btn btn-primary"
                      style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                    >
                      Tải File Word (.docx)
                    </a>
                    <a
                      href="/api/export/srs-md"
                      className="btn btn-outline"
                      style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                    >
                      Tải Markdown (.md)
                    </a>
                  </div>
                </div>

                <div className="doc-preview-box">{result.srs_markdown}</div>
              </div>
            </div>
          )}

          {/* ================================================================
              SCREEN 5: TRACEABILITY MATRIX & JIRA / GITHUB / TRELLO SYNC
              ================================================================ */}
          {activeView === 'sync' && result && (
            <div>
              <div className="toolbar-row">
                <div className="filter-pills">
                  {[
                    { id: 'rtm', label: 'Bảng Ma trận Truy vết (RTM)' },
                    { id: 'jira', label: '1. Đồng bộ Atlassian Jira' },
                    { id: 'github', label: '2. Đồng bộ GitHub Issues' },
                    { id: 'trello', label: '3. Đồng bộ Trello Kanban' },
                  ].map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      className={`pill-btn ${syncTab === t.id ? 'active' : ''}`}
                      onClick={() => {
                        setSyncTab(t.id);
                        setSyncStatus(null);
                      }}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              {syncStatus && (
                <div
                  style={{
                    padding: '12px 16px',
                    borderRadius: '8px',
                    marginBottom: '16px',
                    fontSize: '0.88rem',
                    fontWeight: 600,
                    background: syncStatus.isError ? '#FEF2F2' : '#F0FDF4',
                    border: `1px solid ${syncStatus.isError ? '#FCA5A5' : '#86EFAC'}`,
                    color: syncStatus.isError ? '#B91C1C' : '#166534',
                  }}
                >
                  {syncStatus.msg}
                </div>
              )}

              {syncTab === 'rtm' && (
                <div className="panel-card">
                  <div className="panel-header">
                    <div className="panel-title">
                      Ma trận Truy vết Yêu cầu Thực tế (Requirements Traceability Matrix)
                    </div>
                    <span className="badge badge-ok">Đồng bộ 100% ({totalReqs} yêu cầu)</span>
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Mã Yêu cầu</th>
                          <th>Phân loại</th>
                          <th>Trạng thái</th>
                          <th>Mã Kịch bản</th>
                          <th>Người sử dụng</th>
                          <th>Tên Chức năng (Use Case)</th>
                          <th>Số kịch bản kiểm thử</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.requirements.map((r) => {
                          const us = result.user_stories.find((u) => u.req_id === r.req_id);
                          return (
                            <tr key={r.req_id}>
                              <td>
                                <span className="badge badge-id">{r.req_id}</span>
                              </td>
                              <td>
                                <span className={`badge ${r.req_type === 'FR' ? 'badge-fr' : 'badge-nfr'}`}>
                                  {r.req_type === 'FR'
                                    ? 'Tính năng (FR)'
                                    : `Chất lượng (${ISO_VI_MAP[r.nfr_category] || r.nfr_category || 'NFR'})`}
                                </span>
                              </td>
                              <td>
                                <span className={`badge ${r.is_ambiguous ? 'badge-warn' : 'badge-ok'}`}>
                                  {r.is_ambiguous ? 'Cần làm rõ' : 'Đã rõ ràng'}
                                </span>
                              </td>
                              <td>
                                <strong>{us ? us.story_id : '-'}</strong>
                              </td>
                              <td>{us ? us.role : '-'}</td>
                              <td>{us ? us.puml_usecase_name : '-'}</td>
                              <td>{us ? `${us.acceptance_criteria.length} kịch bản` : '-'}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {syncTab === 'jira' && (
                <div className="panel-card" style={{ maxWidth: '680px' }}>
                  <div className="panel-header">
                    <div className="panel-title">Xuất &amp; Đồng bộ sang Atlassian Jira Cloud</div>
                    <a href="/api/export/jira-csv" className="btn btn-outline">
                      Tải File Jira Import (.csv)
                    </a>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Jira Domain</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="ten-cong-ty.atlassian.net"
                      value={jiraForm.domain}
                      onChange={(e) => setJiraForm({ ...jiraForm, domain: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Email tài khoản Atlassian</label>
                    <input
                      type="email"
                      className="form-input"
                      placeholder="email@company.com"
                      value={jiraForm.email}
                      onChange={(e) => setJiraForm({ ...jiraForm, email: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Atlassian API Token</label>
                    <input
                      type="password"
                      className="form-input"
                      value={jiraForm.token}
                      onChange={(e) => setJiraForm({ ...jiraForm, token: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Mã Dự án (Project Key)</label>
                    <input
                      type="text"
                      className="form-input"
                      value={jiraForm.project_key}
                      onChange={(e) => setJiraForm({ ...jiraForm, project_key: e.target.value })}
                    />
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => handleSyncApi('jira')}
                  >
                    Đẩy trực tiếp lên Jira Cloud
                  </button>
                </div>
              )}

              {syncTab === 'github' && (
                <div className="panel-card" style={{ maxWidth: '680px' }}>
                  <div className="panel-header">
                    <div className="panel-title">Xuất &amp; Đồng bộ sang GitHub Issues</div>
                    <a href="/api/export/github-json" className="btn btn-outline">
                      Tải File GitHub (.json)
                    </a>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Tên Repository (owner/repo)</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="username/repository-name"
                      value={ghForm.repo}
                      onChange={(e) => setGhForm({ ...ghForm, repo: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">GitHub Personal Access Token (PAT)</label>
                    <input
                      type="password"
                      className="form-input"
                      value={ghForm.token}
                      onChange={(e) => setGhForm({ ...ghForm, token: e.target.value })}
                    />
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => handleSyncApi('github')}
                  >
                    Đẩy trực tiếp lên GitHub Issues
                  </button>
                </div>
              )}

              {syncTab === 'trello' && (
                <div className="panel-card" style={{ maxWidth: '680px' }}>
                  <div className="panel-header">
                    <div className="panel-title">Xuất &amp; Đồng bộ sang Trello Kanban</div>
                    <a href="/api/export/trello-json" className="btn btn-outline">
                      Tải File Trello (.json)
                    </a>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Trello API Key</label>
                    <input
                      type="text"
                      className="form-input"
                      value={trelloForm.api_key}
                      onChange={(e) => setTrelloForm({ ...trelloForm, api_key: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Trello Token</label>
                    <input
                      type="password"
                      className="form-input"
                      value={trelloForm.token}
                      onChange={(e) => setTrelloForm({ ...trelloForm, token: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Mã cột Trello (List ID)</label>
                    <input
                      type="text"
                      className="form-input"
                      value={trelloForm.list_id}
                      onChange={(e) => setTrelloForm({ ...trelloForm, list_id: e.target.value })}
                    />
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => handleSyncApi('trello')}
                  >
                    Đẩy trực tiếp lên Trello Board
                  </button>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* ====================================================================
          LIVE 60FPS JAVASCRIPT PIPELINE OVERLAY MODAL DURING ANALYSIS
          ==================================================================== */}
      {isAnalyzing && (
        <div className="pipeline-modal-backdrop">
          <div className="pipeline-modal">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A' }}>
                  AI đang phân tích tài liệu thực tế của bạn...
                </div>
                <div style={{ fontSize: '0.84rem', color: '#64748B', marginTop: '2px' }}>
                  Đang kết nối trực tiếp tới {provider.toUpperCase()} ({modelName})
                </div>
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '1.25rem',
                  fontWeight: 700,
                  color: '#1D4ED8',
                }}
              >
                {(elapsedMs / 1000).toFixed(2)}s
              </div>
            </div>

            <div className="pipeline-step-list">
              {PIPELINE_STEPS.map((stepText, idx) => {
                const stateClass =
                  idx < activeStepIdx ? 'done' : idx === activeStepIdx ? 'active' : '';
                return (
                  <div key={idx} className={`p-step-item ${stateClass}`}>
                    <Icon name={idx < activeStepIdx ? 'check' : 'sparkles'} size={16} />
                    <span>{stepText}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  animateContainerEntrance,
  animateStaggerItems,
  animateSuccessFlash,
  useAnimatedNumber,
} from './animations.js';
import UmlCanvasStudio from './UmlCanvasStudio.jsx';

const ISO_VI_MAP = {
  Performance: 'Tốc độ & Hiệu năng',
  Security: 'Bảo mật & An toàn',
  Usability: 'Dễ sử dụng',
  Reliability: 'Độ ổn định',
  Maintainability: 'Dễ bảo trì & Nâng cấp',
  Portability: 'Chạy trên nhiều thiết bị',
};

const ISO_KEYS = Object.keys(ISO_VI_MAP);

const PIPELINE_STEPS = [
  '1. Đọc tài liệu & Tách thành từng câu yêu cầu',
  '2. Phân biệt Tính năng phần mềm & Yêu cầu chất lượng',
  '3. Tìm các từ viết chung chung & Gợi ý câu viết rõ ràng',
  '4. Viết kịch bản người dùng & Tình huống kiểm tra',
  '5. Vẽ sơ đồ chức năng tổng quan',
  '6. Tạo file Báo cáo Word (.docx) hoàn chỉnh',
];

function Icon({ name, size = 18 }) {
  const props = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: '2',
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
    case 'file':
      return (
        <svg {...props}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
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
    case 'settings':
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      );
    case 'download':
      return (
        <svg {...props}>
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
      );
    case 'arrow-right':
      return (
        <svg {...props}>
          <line x1="5" y1="12" x2="19" y2="12" />
          <polyline points="12 5 19 12 12 19" />
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
          <span key={idx} className="vague-highlight" title="Từ viết còn chung chung, nên làm rõ">
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
  // 3-Step Guided Wizard: 1 (Nhập tài liệu) -> 2 (Kiểm tra & Làm rõ) -> 3 (Nhận Báo cáo Word & Sơ đồ)
  const [step, setStep] = useState(1);

  // Sub-tab inside Step 3: 'report' | 'stories' | 'table' | 'sync'
  const [step3Tab, setStep3Tab] = useState('report');

  // Optional AI Settings Modal state (Hidden from main view so low-tech users aren't overwhelmed)
  const [showAiModal, setShowAiModal] = useState(false);
  const [provider, setProvider] = useState('local_nlp');
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState('TF-IDF + LinearSVC (Bilingual NLP)');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.75);
  const [envDefaults, setEnvDefaults] = useState({});

  // Auth gate (only if server configures APP_PASSWORD)
  const [authStatus, setAuthStatus] = useState({ loading: true, required: false, authenticated: false });
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // Step 1 Input state
  const [projectName, setProjectName] = useState('');
  const [rawText, setRawText] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  // Analysis Job state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeStepIdx, setActiveStepIdx] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [jobMessage, setJobMessage] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [result, setResult] = useState(null);
  const currentJobIdRef = useRef(null);

  // Step 2 Review state
  const [reqFilter, setReqFilter] = useState('all');
  const [reqSearch, setReqSearch] = useState('');
  const [editingReqId, setEditingReqId] = useState(null);
  const [customTextMap, setCustomTextMap] = useState({});
  const [editTypeMap, setEditTypeMap] = useState({});
  const [editCatMap, setEditCatMap] = useState({});
  const [isUpdatingReq, setIsUpdatingReq] = useState(false);

  // Step 3 Sync state
  const [showPlantUmlCode, setShowPlantUmlCode] = useState(false);
  const [syncPlatform, setSyncPlatform] = useState('jira');
  const [jiraForm, setJiraForm] = useState({ domain: '', email: '', token: '', project_key: 'PROJ' });
  const [ghForm, setGhForm] = useState({ repo: '', token: '' });
  const [trelloForm, setTrelloForm] = useState({ api_key: '', token: '', list_id: '' });
  const [syncStatus, setSyncStatus] = useState(null);

  const mainContainerRef = useRef(null);
  const listContainerRef = useRef(null);
  const fileInputRef = useRef(null);

  const loadConfigAndSession = () => {
    fetch('/api/config-defaults')
      .then((r) => r.json())
      .then((d) => {
        setEnvDefaults(d);
        if (typeof d.confidence_threshold === 'number') {
          setConfidenceThreshold(d.confidence_threshold);
        }
        const dp = d.default_provider;
        const isReady =
          dp === 'local_nlp' ||
          dp === 'offline' ||
          (dp === 'ollama' && d.ollama_running) ||
          (dp === 'groq' && d.has_env_groq) ||
          (dp === 'gemini' && d.has_env_gemini) ||
          (dp === 'openrouter' && d.has_env_openrouter);
        if (isReady && dp && dp !== 'offline') {
          setProvider(dp);
          setModelName(d.models?.[dp] || '');
        }
      })
      .catch(() => {});

    // Auto-restore current session if user hits F5
    fetch('/api/session/current')
      .then((r) => r.json())
      .then((d) => {
        if (d?.has_result && d.result) {
          setResult(d.result);
          setStep(2);
        }
      })
      .catch(() => {});
  };

  useEffect(() => {
    fetch('/api/auth/status')
      .then((r) => r.json())
      .then((d) => {
        const authenticated = !d.auth_required || Boolean(d.authenticated);
        setAuthStatus({ loading: false, required: Boolean(d.auth_required), authenticated });
        if (authenticated) loadConfigAndSession();
      })
      .catch(() => {
        setAuthStatus({ loading: false, required: false, authenticated: true });
        loadConfigAndSession();
      });
  }, []);

  useEffect(() => {
    animateContainerEntrance(mainContainerRef.current);
    if (step === 2 || step === 3) {
      animateStaggerItems(listContainerRef.current);
    }
  }, [step, reqFilter, step3Tab]);

  useEffect(() => {
    if (!isAnalyzing) return;
    const start = performance.now();
    let rafId = null;
    const tick = (now) => {
      setElapsedMs(now - start);
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => {
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [isAnalyzing]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoggingIn(true);
    setLoginError('');
    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data.detail || 'Đăng nhập thất bại.');
      setAuthStatus({ loading: false, required: true, authenticated: true });
      setPassword('');
      loadConfigAndSession();
    } catch (err) {
      setLoginError(err.message);
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleProviderChange = (newProv) => {
    setProvider(newProv);
    setErrorMsg('');
    if (newProv === 'local_nlp') setModelName('TF-IDF + LinearSVC (Bilingual NLP)');
    else if (envDefaults.models?.[newProv]) setModelName(envDefaults.models[newProv]);
    else if (newProv === 'groq') setModelName('llama-3.3-70b-versatile');
    else if (newProv === 'gemini') setModelName('gemini-1.5-flash');
    else if (newProv === 'openrouter') setModelName('meta-llama/llama-3.3-70b-instruct:free');
    else if (newProv === 'ollama') setModelName('llama3');
  };

  const hasValidKey =
    provider === 'local_nlp' ||
    provider === 'ollama' ||
    apiKey.trim().length >= 8 ||
    (provider === 'groq' && envDefaults.has_env_groq) ||
    (provider === 'gemini' && envDefaults.has_env_gemini) ||
    (provider === 'openrouter' && envDefaults.has_env_openrouter);

  const totalReqs = result ? result.requirements.length : 0;
  const frCount = result ? result.requirements.filter((r) => r.req_type === 'FR').length : 0;
  const nfrCount = result ? result.requirements.filter((r) => r.req_type === 'NFR').length : 0;
  const ambiguousCount = result ? result.requirements.filter((r) => r.is_ambiguous).length : 0;
  const cleanCount = totalReqs - ambiguousCount;

  const animTotal = useAnimatedNumber(totalReqs);
  const animClean = useAnimatedNumber(cleanCount);

  const filteredRequirements = useMemo(() => {
    if (!result) return [];
    return result.requirements.filter((r) => {
      if (reqFilter === 'ambiguous' && !r.is_ambiguous) return false;
      if (reqFilter === 'clean' && r.is_ambiguous) return false;
      if (reqSearch.trim()) {
        const q = reqSearch.trim().toLowerCase();
        if (!r.req_id.toLowerCase().includes(q) && !r.raw_text.toLowerCase().includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [result, reqFilter, reqSearch]);

  const handleRunAnalysis = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!hasValidKey) {
      setShowAiModal(true);
      setErrorMsg('Bạn đang chọn chế độ AI trực tuyến nhưng chưa nhập API Key. Hãy nhập API Key hoặc chuyển về Chế độ Tự động trên máy.');
      return;
    }

    if (!selectedFile && !rawText.trim()) {
      setErrorMsg('Bạn hãy chọn một file tài liệu (.docx hoặc .txt) hoặc gõ nội dung mô tả vào ô bên dưới nhé.');
      return;
    }

    setIsAnalyzing(true);
    setActiveStepIdx(0);
    setJobMessage('Đang đọc tài liệu của bạn...');
    currentJobIdRef.current = null;

    try {
      const formData = new FormData();
      formData.append('provider', provider);
      formData.append('api_key', apiKey.trim());
      formData.append('model_name', modelName.trim());
      formData.append('confidence_threshold', String(confidenceThreshold));
      formData.append('project_name', projectName.trim());
      formData.append('raw_text', rawText);
      if (selectedFile) {
        formData.append('file', selectedFile);
      }

      const resp = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });

      const submitted = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(submitted.detail || 'Không thể phân tích tài liệu.');
      }

      if (submitted.job_id) {
        currentJobIdRef.current = submitted.job_id;
        let job = null;
        while (true) {
          const jobResp = await fetch(`/api/jobs/${submitted.job_id}`);
          const jobData = await jobResp.json().catch(() => ({}));
          if (!jobResp.ok) {
            throw new Error(jobData.detail || 'Không đọc được tiến trình xử lý.');
          }
          job = jobData;
          if (job.message) setJobMessage(job.message);
          if (typeof job.step === 'number' && job.step > 0) {
            setActiveStepIdx(Math.min(job.step - 1, PIPELINE_STEPS.length - 1));
          }
          if (job.status === 'succeeded') break;
          if (job.status === 'failed') {
            throw new Error(job.error || 'Quá trình phân tích gặp sự cố.');
          }
          if (job.status === 'cancelled') {
            throw new Error('Đã dừng phân tích theo yêu cầu.');
          }
          await new Promise((resolve) => setTimeout(resolve, 400));
        }
        setResult(job.result);
      } else {
        setResult(submitted);
      }

      setStep(2);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      currentJobIdRef.current = null;
      setIsAnalyzing(false);
    }
  };

  const handleCancelAnalysis = async () => {
    const jobId = currentJobIdRef.current;
    if (!jobId) return;
    try {
      await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
    } catch {}
  };

  const handleAcceptSuggestion = async (reqId, suggestedText, cardEl) => {
    setIsUpdatingReq(true);
    try {
      const resp = await fetch(`/api/requirements/${reqId}/apply-smart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_text: suggestedText }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setResult(data);
        setEditingReqId(null);
        animateSuccessFlash(cardEl || mainContainerRef.current);
      }
    } finally {
      setIsUpdatingReq(false);
    }
  };

  const handleAcceptAllSuggestions = async () => {
    setIsUpdatingReq(true);
    try {
      const resp = await fetch('/api/requirements/apply-smart-all', { method: 'POST' });
      const data = await resp.json();
      if (resp.ok) {
        setResult(data);
        animateSuccessFlash(mainContainerRef.current);
      }
    } finally {
      setIsUpdatingReq(false);
    }
  };

  const handleSaveCustomEdit = async (req) => {
    setIsUpdatingReq(true);
    try {
      const newText = (customTextMap[req.req_id] ?? req.raw_text).trim();
      const newType = editTypeMap[req.req_id] ?? req.req_type;
      const newCat = editCatMap[req.req_id] ?? (req.nfr_category || 'Performance');

      if (newText && newText !== req.raw_text) {
        await fetch(`/api/requirements/${req.req_id}/apply-smart`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ new_text: newText }),
        });
      }

      const resp = await fetch(`/api/requirements/${req.req_id}/update-type`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          req_type: newType,
          nfr_category: newType === 'NFR' ? newCat : null,
        }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setResult(data);
        setEditingReqId(null);
      }
    } finally {
      setIsUpdatingReq(false);
    }
  };

  const handleSyncApi = async (platform) => {
    setSyncStatus({ loading: true, msg: 'Đang gửi dữ liệu...', isError: false });
    try {
      let url = '/api/sync/jira';
      let payload = jiraForm;
      if (platform === 'github') {
        url = '/api/sync/github';
        payload = ghForm;
      } else if (platform === 'trello') {
        url = '/api/sync/trello';
        payload = trelloForm;
      }
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Lỗi kết nối');
      if (data.errors?.length > 0) {
        setSyncStatus({
          loading: false,
          msg: `Đã tạo ${data.success_count}, lỗi ${data.errors.length}: ${data.errors[0].error}`,
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

  if (authStatus.loading) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <div className="brand-name">BA-Gen</div>
          <p style={{ color: '#64748B', marginTop: '6px' }}>Đang khởi tạo ứng dụng...</p>
        </div>
      </div>
    );
  }

  if (authStatus.required && !authStatus.authenticated) {
    return (
      <div className="auth-screen">
        <form className="auth-card" onSubmit={handleLogin}>
          <div className="brand-group" style={{ marginBottom: '18px' }}>
            <div className="brand-icon">
              <Icon name="file" size={20} />
            </div>
            <div>
              <div className="brand-name">BA-Gen</div>
              <div className="brand-tagline">Nhập mật khẩu để truy cập</div>
            </div>
          </div>
          <label className="field-label" htmlFor="app-password">
            Mật khẩu
          </label>
          <input
            id="app-password"
            className="input-field"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
          />
          {loginError && (
            <div style={{ color: '#B91C1C', fontSize: '0.85rem', marginTop: '8px' }}>
              {loginError}
            </div>
          )}
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            style={{ marginTop: '14px' }}
            disabled={isLoggingIn}
          >
            {isLoggingIn ? 'Đang kiểm tra...' : 'Đăng nhập'}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div>
      {/* ====================================================================
          TOP HEADER BAR WITH SIMPLE 3-STEP WIZARD STEPPER
          ==================================================================== */}
      <header className="wizard-header">
        <div className="wizard-header-inner">
          <div className="brand-group">
            <div className="brand-icon">
              <Icon name="file" size={20} />
            </div>
            <div>
              <div className="brand-name">BA-Gen</div>
              <div className="brand-tagline">Trợ lý Viết Tài liệu Yêu cầu Phần mềm</div>
            </div>
          </div>

          {/* 3-STEP VISUAL WORKFLOW */}
          <nav className="stepper-nav" aria-label="Quy trình 3 bước">
            <button
              type="button"
              className={`step-pill ${step === 1 ? 'active' : result ? 'completed' : ''}`}
              onClick={() => setStep(1)}
            >
              <span className="step-circle">{result && step !== 1 ? '✓' : '1'}</span>
              <span>Bước 1: Nhập tài liệu</span>
            </button>

            <span className="step-arrow">→</span>

            <button
              type="button"
              disabled={!result}
              className={`step-pill ${step === 2 ? 'active' : step > 2 ? 'completed' : ''}`}
              onClick={() => setStep(2)}
            >
              <span className="step-circle">{step > 2 ? '✓' : '2'}</span>
              <span>Bước 2: Kiểm tra &amp; Làm rõ câu</span>
            </button>

            <span className="step-arrow">→</span>

            <button
              type="button"
              disabled={!result}
              className={`step-pill ${step === 3 ? 'active' : ''}`}
              onClick={() => setStep(3)}
            >
              <span className="step-circle">3</span>
              <span>Bước 3: Tải Báo cáo Word &amp; Sơ đồ</span>
            </button>
          </nav>

          {/* OPTIONAL AI SETTINGS BUTTON (KEPT QUIET IN CORNER) */}
          <div className="header-actions">
            <button
              type="button"
              className="btn btn-outline"
              style={{ padding: '7px 13px', fontSize: '0.84rem' }}
              onClick={() => setShowAiModal(true)}
            >
              <Icon name="settings" size={16} />
              <span>
                {provider === 'local_nlp'
                  ? 'Chế độ: Tự động trên máy'
                  : `AI: ${provider.toUpperCase()}`}
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* ====================================================================
          MAIN GUIDED WORKSPACE
          ==================================================================== */}
      <main
        className={`wizard-main ${step === 1 ? 'narrow' : ''}`}
        ref={mainContainerRef}
      >
        {/* ==================================================================
            BƯỚC 1: NHẬP TÀI LIỆU HOẶC Ý TƯỞNG (GỌN GÀNG, DỄ HIỂU 100%)
            ================================================================== */}
        {step === 1 && (
          <div>
            <div className="hero-intro">
              <h1>Bước 1: Đưa tài liệu hoặc mô tả phần mềm vào đây</h1>
              <p>
                Bạn chỉ cần tải file Word (<code>.docx</code>) lên hoặc dán đoạn văn mô tả yêu cầu.
                Hệ thống sẽ tự động tách từng ý, gợi ý sửa những câu viết còn chung chung và xuất sẵn file Báo cáo Word.
              </p>
            </div>

            <form className="card" onSubmit={handleRunAnalysis}>
              {errorMsg && (
                <div
                  style={{
                    background: '#FEF2F2',
                    border: '1px solid #FCA5A5',
                    color: '#B91C1C',
                    padding: '12px 16px',
                    borderRadius: '10px',
                    fontSize: '0.9rem',
                    marginBottom: '18px',
                    fontWeight: 500,
                  }}
                >
                  {errorMsg}
                </div>
              )}

              {/* 1. FILE UPLOAD BOX */}
              <div>
                <label className="field-label">
                  Cách 1: Chọn file tài liệu từ máy tính (.docx hoặc .txt)
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".docx,.txt"
                  style={{ display: 'none' }}
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                />
                <div
                  className={`upload-box ${selectedFile ? 'has-file' : ''}`}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="upload-icon-circle">
                    <Icon name={selectedFile ? 'check' : 'upload'} size={22} />
                  </div>
                  {selectedFile ? (
                    <div>
                      <div style={{ fontWeight: 700, color: '#15803D', fontSize: '1rem' }}>
                        Đã chọn file: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                      </div>
                      <div style={{ fontSize: '0.84rem', color: '#166534', marginTop: '4px' }}>
                        Bạn có thể bấm nút "Bắt đầu Phân tích" ở dưới ngay, hoặc bấm vào đây để chọn file khác
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div style={{ fontWeight: 700, color: '#1D4ED8', fontSize: '1rem' }}>
                        Bấm vào đây để chọn file Word (.docx) hoặc file văn bản (.txt)
                      </div>
                      <div style={{ fontSize: '0.84rem', color: '#64748B', marginTop: '4px' }}>
                        Đọc được cả nội dung chữ lẫn các bảng biểu bên trong file Word
                      </div>
                    </div>
                  )}
                </div>

                {selectedFile && (
                  <div style={{ marginTop: '8px', textAlign: 'right' }}>
                    <button
                      type="button"
                      className="btn btn-outline"
                      style={{ padding: '5px 12px', fontSize: '0.8rem' }}
                      onClick={() => setSelectedFile(null)}
                    >
                      Bỏ chọn file này
                    </button>
                  </div>
                )}
              </div>

              <div className="or-divider">HOẶC</div>

              {/* 2. PASTE RAW TEXT */}
              <div style={{ marginBottom: '18px' }}>
                <label className="field-label">
                  Cách 2: Gõ hoặc dán trực tiếp nội dung mô tả yêu cầu vào ô dưới đây
                </label>
                <textarea
                  className="textarea-field"
                  placeholder={
                    'Ví dụ:\n' +
                    '- Khách hàng có thể đăng ký tài khoản và đặt mua sản phẩm trực tuyến.\n' +
                    '- Trang thanh toán của phần mềm phải chạy thật nhanh và dễ sử dụng.'
                  }
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                />
              </div>

              {/* 3. OPTIONAL PROJECT NAME */}
              <div style={{ marginBottom: '22px' }}>
                <label className="field-label">
                  Tên dự án / phần mềm của bạn (Không bắt buộc)
                </label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Ví dụ: Phần mềm Quản lý Bán hàng (Nếu để trống sẽ tự lấy theo tên file)"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                />
              </div>

              <button type="submit" className="btn btn-primary btn-lg" disabled={isAnalyzing}>
                <Icon name="sparkles" size={20} />
                <span>Bắt đầu Phân tích Tài liệu →</span>
              </button>
            </form>

            {/* 3 MINI EXPLANATION CARDS */}
            <div className="how-it-works-grid">
              <div className="mini-guide-card">
                <div className="mini-guide-num">Kết quả 1</div>
                <div className="mini-guide-title">Sửa các câu viết chung chung</div>
                <div className="mini-guide-desc">
                  Tự động phát hiện các từ mơ hồ như <em>"nhanh", "dễ dùng"</em> và gợi ý câu viết lại rõ ràng, có con số cụ thể.
                </div>
              </div>
              <div className="mini-guide-card">
                <div className="mini-guide-num">Kết quả 2</div>
                <div className="mini-guide-title">Kịch bản &amp; Sơ đồ trực quan</div>
                <div className="mini-guide-desc">
                  Diễn giải rõ ai là người dùng, họ muốn làm gì và tự động vẽ sơ đồ tổng quan các chức năng của hệ thống.
                </div>
              </div>
              <div className="mini-guide-card">
                <div className="mini-guide-num">Kết quả 3</div>
                <div className="mini-guide-title">File Báo cáo Word (.docx)</div>
                <div className="mini-guide-desc">
                  Tạo sẵn file tài liệu đặc tả phần mềm 6 phần bài bản để bạn tải về máy chỉ với 1 cú nhấp chuột.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================================================================
            BƯỚC 2: KIỂM TRA & LÀM RÕ CÁC CÂU YÊU CẦU (RÕ RÀNG, TỪNG CÂU MỘT)
            ================================================================== */}
        {step === 2 && result && (
          <div>
            {result.warnings?.length > 0 && (
              <div
                style={{
                  background: '#FFFBEB',
                  border: '1px solid #FCD34D',
                  color: '#92400E',
                  padding: '12px 16px',
                  borderRadius: '10px',
                  marginBottom: '16px',
                  fontSize: '0.9rem',
                }}
              >
                {result.warnings.map((w, i) => (
                  <div key={i}>{w}</div>
                ))}
              </div>
            )}

            {/* GUIDED ACTION BANNER */}
            <div className={`guided-banner ${ambiguousCount > 0 ? 'has-warnings' : 'all-clean'}`}>
              <div style={{ flex: 1, minWidth: '260px' }}>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0F172A', marginBottom: '4px' }}>
                  {ambiguousCount > 0
                    ? `Tìm thấy ${animTotal} yêu cầu — Có ${ambiguousCount} câu nên viết rõ ràng hơn`
                    : `Tuyệt vời! Cả ${animTotal} câu yêu cầu của bạn đều đã rất rõ ràng`}
                </div>
                <div style={{ fontSize: '0.9rem', color: '#475569' }}>
                  {ambiguousCount > 0
                    ? 'Những câu có khung màu xanh lá bên dưới là những câu đang dùng từ chung chung (như "nhanh", "dễ dùng"). Bạn có thể bấm nút áp dụng gợi ý để làm rõ ngay.'
                    : `Gồm ${frCount} tính năng phần mềm và ${nfrCount} yêu cầu về chất lượng/tốc độ. Bạn có thể bấm tiếp tục sang Bước 3 để tải file Báo cáo Word.`}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                {ambiguousCount > 0 && (
                  <button
                    type="button"
                    className="btn btn-success"
                    disabled={isUpdatingReq}
                    onClick={handleAcceptAllSuggestions}
                  >
                    <Icon name="sparkles" size={17} />
                    <span>Tự động làm rõ cả {ambiguousCount} câu này</span>
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setStep(3)}
                >
                  <span>Sang Bước 3: Tải Báo cáo Word &amp; Sơ đồ</span>
                  <Icon name="arrow-right" size={17} />
                </button>
              </div>
            </div>

            {/* SIMPLE 3-OPTION FILTER BAR */}
            <div className="filter-bar">
              <div className="filter-tabs">
                <button
                  type="button"
                  className={`filter-tab ${reqFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setReqFilter('all')}
                >
                  Tất cả ({totalReqs} câu)
                </button>
                <button
                  type="button"
                  className={`filter-tab ${reqFilter === 'ambiguous' ? 'active' : ''}`}
                  onClick={() => setReqFilter('ambiguous')}
                >
                  Cần làm rõ thêm ({ambiguousCount} câu)
                </button>
                <button
                  type="button"
                  className={`filter-tab ${reqFilter === 'clean' ? 'active' : ''}`}
                  onClick={() => setReqFilter('clean')}
                >
                  Đã rõ ràng ({animClean} câu)
                </button>
              </div>

              <input
                type="text"
                className="input-field"
                style={{ width: '250px', padding: '8px 14px', fontSize: '0.88rem' }}
                placeholder="Tìm nhanh theo từ khóa..."
                value={reqSearch}
                onChange={(e) => setReqSearch(e.target.value)}
              />
            </div>

            {/* SINGLE-COLUMN SPACIOUS REQUIREMENT CARDS */}
            <div ref={listContainerRef}>
              {filteredRequirements.map((req, index) => {
                const isEditing = editingReqId === req.req_id;
                const categoryVi = req.nfr_category
                  ? ISO_VI_MAP[req.nfr_category] || req.nfr_category
                  : null;

                return (
                  <div
                    key={req.req_id}
                    className={`req-review-card js-stagger-item ${
                      req.is_ambiguous ? 'needs-attention' : ''
                    }`}
                  >
                    <div className="req-card-top">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span className="badge badge-num">Câu #{index + 1} ({req.req_id})</span>
                        <span className={`badge ${req.req_type === 'FR' ? 'badge-fr' : 'badge-nfr'}`}>
                          {req.req_type === 'FR'
                            ? 'Tính năng phần mềm'
                            : `Yêu cầu chất lượng${categoryVi ? ` · ${categoryVi}` : ''}`}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span className={`badge ${req.is_ambiguous ? 'badge-warn' : 'badge-ok'}`}>
                          {req.is_ambiguous ? 'Đang viết hơi chung chung' : '✓ Đã viết rõ ràng'}
                        </span>
                        <button
                          type="button"
                          className="btn btn-outline"
                          style={{ padding: '4px 10px', fontSize: '0.78rem', borderRadius: '6px' }}
                          onClick={() => {
                            if (isEditing) {
                              setEditingReqId(null);
                            } else {
                              setCustomTextMap((prev) => ({
                                ...prev,
                                [req.req_id]: req.smart_rewrite || req.raw_text,
                              }));
                              setEditTypeMap((prev) => ({ ...prev, [req.req_id]: req.req_type }));
                              setEditCatMap((prev) => ({
                                ...prev,
                                [req.req_id]: req.nfr_category || 'Performance',
                              }));
                              setEditingReqId(req.req_id);
                            }
                          }}
                        >
                          {isEditing ? 'Đóng khung sửa' : 'Tự sửa câu này'}
                        </button>
                      </div>
                    </div>

                    {/* SENTENCE CONTENT */}
                    <div className="req-sentence">
                      <HighlightedText text={req.raw_text} vagueTerms={req.vague_terms} />
                    </div>

                    {/* IF AMBIGUOUS: SHOW CLEAN 1-CLICK SUGGESTION */}
                    {req.is_ambiguous && req.smart_rewrite && !isEditing && (
                      <div className="suggestion-panel">
                        <div className="suggestion-reason">
                          <strong>Điểm cần làm rõ: </strong>
                          {req.vague_terms?.length > 0 && (
                            <span>
                              Câu này đang dùng từ cảm tính (<strong>{req.vague_terms.join(', ')}</strong>) chưa có con số đo lường cụ thể.{' '}
                            </span>
                          )}
                          {req.missing_actor && (
                            <span>Chưa ghi rõ ai là người thực hiện tính năng này. </span>
                          )}
                          {req.missing_metric && (
                            <span>Chưa có con số tiêu chuẩn cụ thể (ví dụ: bao nhiêu giây, bao nhiêu %).</span>
                          )}
                        </div>

                        <div className="suggestion-row">
                          <div className="suggestion-text">
                            <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#15803D', marginBottom: '2px' }}>
                              GỢI Ý VIẾT LẠI RÕ RÀNG HƠN:
                            </div>
                            {req.smart_rewrite}
                          </div>

                          <button
                            type="button"
                            className="btn btn-success"
                            style={{ flexShrink: 0 }}
                            disabled={isUpdatingReq}
                            onClick={(e) =>
                              handleAcceptSuggestion(
                                req.req_id,
                                req.smart_rewrite,
                                e.currentTarget.closest('.req-review-card')
                              )
                            }
                          >
                            <Icon name="check" size={16} />
                            <span>Dùng câu gợi ý này</span>
                          </button>
                        </div>
                      </div>
                    )}

                    {/* OPTIONAL INLINE EDITOR (ONLY SHOWN WHEN USER CLICKS "TỰ SỬA CÂU NÀY") */}
                    {isEditing && (
                      <div
                        style={{
                          marginTop: '14px',
                          padding: '16px',
                          background: '#F8FAFC',
                          border: '1px solid #CBD5E1',
                          borderRadius: '10px',
                        }}
                      >
                        <label className="field-label" style={{ fontSize: '0.84rem' }}>
                          Sửa lại nội dung câu yêu cầu theo ý bạn:
                        </label>
                        <textarea
                          className="textarea-field"
                          style={{ minHeight: '85px', marginBottom: '12px', fontSize: '0.92rem' }}
                          value={customTextMap[req.req_id] ?? req.raw_text}
                          onChange={(e) =>
                            setCustomTextMap((prev) => ({ ...prev, [req.req_id]: e.target.value }))
                          }
                        />

                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: '12px',
                            flexWrap: 'wrap',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                            <span style={{ fontSize: '0.84rem', fontWeight: 600, color: '#475569' }}>
                              Nhóm yêu cầu:
                            </span>
                            <select
                              className="select-field"
                              style={{ width: 'auto', padding: '7px 12px', fontSize: '0.86rem' }}
                              value={editTypeMap[req.req_id] ?? req.req_type}
                              onChange={(e) =>
                                setEditTypeMap((prev) => ({ ...prev, [req.req_id]: e.target.value }))
                              }
                            >
                              <option value="FR">Tính năng phần mềm</option>
                              <option value="NFR">Yêu cầu chất lượng / tốc độ</option>
                            </select>

                            {(editTypeMap[req.req_id] ?? req.req_type) === 'NFR' && (
                              <select
                                className="select-field"
                                style={{ width: 'auto', padding: '7px 12px', fontSize: '0.86rem' }}
                                value={editCatMap[req.req_id] ?? (req.nfr_category || 'Performance')}
                                onChange={(e) =>
                                  setEditCatMap((prev) => ({ ...prev, [req.req_id]: e.target.value }))
                                }
                              >
                                {ISO_KEYS.map((k) => (
                                  <option key={k} value={k}>
                                    {ISO_VI_MAP[k]}
                                  </option>
                                ))}
                              </select>
                            )}
                          </div>

                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                              type="button"
                              className="btn btn-outline"
                              style={{ padding: '7px 14px', fontSize: '0.85rem' }}
                              onClick={() => setEditingReqId(null)}
                            >
                              Hủy
                            </button>
                            <button
                              type="button"
                              className="btn btn-primary"
                              style={{ padding: '7px 16px', fontSize: '0.85rem' }}
                              disabled={isUpdatingReq}
                              onClick={() => handleSaveCustomEdit(req)}
                            >
                              Lưu thay đổi
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {filteredRequirements.length === 0 && (
                <div className="card" style={{ textAlign: 'center', color: '#64748B' }}>
                  Không có câu yêu cầu nào trong mục này.
                </div>
              )}
            </div>

            {/* BOTTOM STEP NAVIGATION */}
            <div className="step-footer">
              <button type="button" className="btn btn-outline" onClick={() => setStep(1)}>
                ← Quay lại Bước 1 (Đổi tài liệu khác)
              </button>
              <button type="button" className="btn btn-primary" onClick={() => setStep(3)}>
                <span>Tiếp tục sang Bước 3: Tải Báo cáo Word &amp; Sơ đồ</span>
                <Icon name="arrow-right" size={18} />
              </button>
            </div>
          </div>
        )}

        {/* ==================================================================
            BƯỚC 3: NHẬN BÁO CÁO WORD (.DOCX), SƠ ĐỒ & KỊCH BẢN NGƯỜI DÙNG
            ================================================================== */}
        {step === 3 && result && (
          <div>
            {/* TOP DELIVERABLE DOWNLOAD CARDS */}
            <div className="deliverable-grid">
              <div className="deliverable-card primary-highlight">
                <div>
                  <span className="badge badge-ok" style={{ marginBottom: '10px' }}>
                    ✓ Đã tạo xong báo cáo hoàn chỉnh
                  </span>
                  <h2 style={{ fontSize: '1.22rem', fontWeight: 700, marginBottom: '6px' }}>
                    1. File Báo cáo Đặc tả Phần mềm (.docx)
                  </h2>
                  <p style={{ fontSize: '0.88rem', color: '#475569' }}>
                    Tài liệu Microsoft Word đã được trình bày sẵn thành 6 phần đầy đủ: Giới thiệu dự án,
                    Danh sách người dùng, Các tính năng, Tiêu chuẩn chất lượng, Kịch bản và Bảng tổng hợp.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  <a href="/api/export/srs-docx" className="btn btn-primary">
                    <Icon name="download" size={18} />
                    <span>Tải về File Word (.docx)</span>
                  </a>
                  <a href="/api/export/srs-md" className="btn btn-outline">
                    <span>Tải bản Văn bản (.md)</span>
                  </a>
                </div>
              </div>

              <div className="deliverable-card">
                <div>
                  <span className="badge badge-nfr" style={{ marginBottom: '10px' }}>
                    Hình vẽ minh họa hệ thống
                  </span>
                  <h2 style={{ fontSize: '1.22rem', fontWeight: 700, marginBottom: '6px' }}>
                    2. Sơ đồ Chức năng Tổng quan (Use Case)
                  </h2>
                  <p style={{ fontSize: '0.88rem', color: '#475569' }}>
                    Hình ảnh sơ đồ trực quan giúp bất kỳ ai nhìn vào cũng biết hệ thống có những nhóm người dùng nào
                    và họ sử dụng các chức năng gì.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  {result.has_diagram_image && (
                    <a
                      href="/api/export/diagram-png"
                      download={`${result.project.project_name}_usecase.png`}
                      className="btn btn-primary"
                    >
                      <Icon name="download" size={18} />
                      <span>Tải Hình ảnh Sơ đồ (.png)</span>
                    </a>
                  )}
                  <a
                    href="/api/export/diagram-puml"
                    download={`${result.project.project_name}_usecase.puml`}
                    className="btn btn-outline"
                  >
                    <span>Tải file vẽ kỹ thuật (.puml)</span>
                  </a>
                </div>
              </div>
            </div>

            {/* 4 CLEAN SUB-TABS TO INSPECT DETAILS ON SCREEN */}
            <div className="sub-tabs-bar">
              <button
                type="button"
                className={`sub-tab-btn ${step3Tab === 'report' ? 'active' : ''}`}
                onClick={() => setStep3Tab('report')}
              >
                Xem Sơ đồ &amp; Nội dung Báo cáo
              </button>
              <button
                type="button"
                className={`sub-tab-btn ${step3Tab === 'stories' ? 'active' : ''}`}
                onClick={() => setStep3Tab('stories')}
              >
                Kịch bản Người dùng ({result.user_stories.length})
              </button>
              <button
                type="button"
                className={`sub-tab-btn ${step3Tab === 'table' ? 'active' : ''}`}
                onClick={() => setStep3Tab('table')}
              >
                Bảng Tổng hợp Yêu cầu ({totalReqs})
              </button>
              <button
                type="button"
                className={`sub-tab-btn ${step3Tab === 'sync' ? 'active' : ''}`}
                onClick={() => setStep3Tab('sync')}
              >
                Xuất sang Jira / GitHub / Trello
              </button>
            </div>

            {/* SUB-TAB 1: INTERACTIVE WEB UML STUDIO & REPORT PREVIEW */}
            {step3Tab === 'report' && (
              <div ref={listContainerRef}>
                <UmlCanvasStudio
                  userStories={result.user_stories}
                  projectName={result.project?.project_name || 'Hệ thống Phần mềm'}
                  initialPlantUmlCode={result.plantuml_code}
                  hasKrokiImage={result.has_diagram_image}
                />

                <div className="card">
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '12px' }}>
                    Xem trước Nội dung Báo cáo Đặc tả Phần mềm
                  </h3>
                  <div className="doc-preview-box">{result.srs_markdown}</div>
                </div>
              </div>
            )}

            {/* SUB-TAB 2: USER STORIES IN PLAIN VIETNAMESE */}
            {step3Tab === 'stories' && (
              <div ref={listContainerRef}>
                {result.user_stories.map((us, idx) => (
                  <div key={us.story_id} className="story-simple-card js-stagger-item">
                    <div className="req-card-top">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span className="badge badge-num">Kịch bản #{idx + 1} ({us.story_id})</span>
                        <span className="badge badge-fr">Tên chức năng: {us.puml_usecase_name}</span>
                        <span className="badge badge-nfr">Từ yêu cầu: {us.req_id}</span>
                      </div>
                    </div>

                    <div className="story-rgb-row">
                      <div className="story-rgb-box">
                        <div className="story-rgb-label">1. Ai là người sử dụng?</div>
                        <div className="story-rgb-val">{us.role}</div>
                      </div>
                      <div className="story-rgb-box">
                        <div className="story-rgb-label">2. Họ muốn làm việc gì?</div>
                        <div className="story-rgb-val">{us.goal}</div>
                      </div>
                      <div className="story-rgb-box">
                        <div className="story-rgb-label">3. Để mang lại lợi ích gì?</div>
                        <div className="story-rgb-val">{us.benefit}</div>
                      </div>
                    </div>

                    <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#334155', marginTop: '10px' }}>
                      Các tình huống kiểm tra để nghiệm thu tính năng này:
                    </div>
                    {us.acceptance_criteria.map((ac, acIdx) => (
                      <div key={acIdx} className="test-check-box">
                        <div style={{ fontWeight: 700, color: '#1D4ED8', marginBottom: '6px' }}>
                          Tình huống {acIdx + 1}: {ac.scenario}
                        </div>
                        <div>
                          <strong>• Điều kiện ban đầu:</strong> {ac.given}
                        </div>
                        <div>
                          <strong>• Khi người dùng thao tác:</strong> {ac.when}
                        </div>
                        <div>
                          <strong>• Kết quả phần mềm phải đạt:</strong> {ac.then}
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}

            {/* SUB-TAB 3: SUMMARY TABLE */}
            {step3Tab === 'table' && (
              <div className="card" ref={listContainerRef}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '14px' }}>
                  Bảng Tổng hợp Toàn bộ Yêu cầu &amp; Kịch bản
                </h3>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Mã</th>
                        <th>Nội dung yêu cầu</th>
                        <th>Nhóm yêu cầu</th>
                        <th>Người sử dụng</th>
                        <th>Tên chức năng</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.requirements.map((r) => {
                        const us = result.user_stories.find((u) => u.req_id === r.req_id);
                        return (
                          <tr key={r.req_id}>
                            <td>
                              <strong>{r.req_id}</strong>
                            </td>
                            <td>{r.raw_text}</td>
                            <td>
                              <span className={`badge ${r.req_type === 'FR' ? 'badge-fr' : 'badge-nfr'}`}>
                                {r.req_type === 'FR'
                                  ? 'Tính năng'
                                  : `Chất lượng (${ISO_VI_MAP[r.nfr_category] || r.nfr_category || 'NFR'})`}
                              </span>
                            </td>
                            <td>{us ? us.role : '-'}</td>
                            <td>{us ? us.puml_usecase_name : '-'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* SUB-TAB 4: JIRA / GITHUB / TRELLO EXPORT */}
            {step3Tab === 'sync' && (
              <div className="card" ref={listContainerRef}>
                <div style={{ marginBottom: '18px' }}>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '4px' }}>
                    Xuất danh sách công việc sang Phần mềm Quản lý Dự án
                  </h3>
                  <p style={{ fontSize: '0.88rem', color: '#64748B' }}>
                    Bạn có thể tải file về máy ngay (không cần tài khoản) hoặc điền thông tin kết nối để đẩy thẳng lên dự án.
                  </p>
                </div>

                <div className="filter-tabs" style={{ marginBottom: '18px' }}>
                  <button
                    type="button"
                    className={`filter-tab ${syncPlatform === 'jira' ? 'active' : ''}`}
                    onClick={() => {
                      setSyncPlatform('jira');
                      setSyncStatus(null);
                    }}
                  >
                    1. Phần mềm Jira
                  </button>
                  <button
                    type="button"
                    className={`filter-tab ${syncPlatform === 'github' ? 'active' : ''}`}
                    onClick={() => {
                      setSyncPlatform('github');
                      setSyncStatus(null);
                    }}
                  >
                    2. GitHub Issues
                  </button>
                  <button
                    type="button"
                    className={`filter-tab ${syncPlatform === 'trello' ? 'active' : ''}`}
                    onClick={() => {
                      setSyncPlatform('trello');
                      setSyncStatus(null);
                    }}
                  >
                    3. Bảng Trello
                  </button>
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

                {syncPlatform === 'jira' && (
                  <div>
                    <div style={{ marginBottom: '16px' }}>
                      <a href="/api/export/jira-csv" className="btn btn-primary">
                        <Icon name="download" size={17} />
                        <span>Tải File Bảng tính Jira (.csv) về máy ngay</span>
                      </a>
                    </div>
                    <div style={{ borderTop: '1px solid #E2E8F0', paddingTop: '16px', maxWidth: '520px' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.92rem', marginBottom: '12px' }}>
                        Hoặc đẩy trực tiếp lên Jira Cloud:
                      </div>
                      <div style={{ marginBottom: '10px' }}>
                        <label className="field-label">Địa chỉ Jira Domain</label>
                        <input
                          type="text"
                          className="input-field"
                          placeholder="ten-cong-ty.atlassian.net"
                          value={jiraForm.domain}
                          onChange={(e) => setJiraForm({ ...jiraForm, domain: e.target.value })}
                        />
                      </div>
                      <div style={{ marginBottom: '10px' }}>
                        <label className="field-label">Email đăng nhập Jira</label>
                        <input
                          type="email"
                          className="input-field"
                          placeholder="email@company.com"
                          value={jiraForm.email}
                          onChange={(e) => setJiraForm({ ...jiraForm, email: e.target.value })}
                        />
                      </div>
                      <div style={{ marginBottom: '10px' }}>
                        <label className="field-label">Mã Jira API Token</label>
                        <input
                          type="password"
                          className="input-field"
                          value={jiraForm.token}
                          onChange={(e) => setJiraForm({ ...jiraForm, token: e.target.value })}
                        />
                      </div>
                      <div style={{ marginBottom: '14px' }}>
                        <label className="field-label">Mã Dự án (Project Key)</label>
                        <input
                          type="text"
                          className="input-field"
                          value={jiraForm.project_key}
                          onChange={(e) => setJiraForm({ ...jiraForm, project_key: e.target.value })}
                        />
                      </div>
                      <button
                        type="button"
                        className="btn btn-outline"
                        onClick={() => handleSyncApi('jira')}
                      >
                        Đẩy trực tiếp lên Jira Cloud
                      </button>
                    </div>
                  </div>
                )}

                {syncPlatform === 'github' && (
                  <div>
                    <div style={{ marginBottom: '16px' }}>
                      <a href="/api/export/github-json" className="btn btn-primary">
                        <Icon name="download" size={17} />
                        <span>Tải File GitHub Issues (.json) về máy ngay</span>
                      </a>
                    </div>
                    <div style={{ borderTop: '1px solid #E2E8F0', paddingTop: '16px', maxWidth: '520px' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.92rem', marginBottom: '12px' }}>
                        Hoặc đẩy trực tiếp lên kho GitHub:
                      </div>
                      <div style={{ marginBottom: '10px' }}>
                        <label className="field-label">Tên kho GitHub (owner/repo)</label>
                        <input
                          type="text"
                          className="input-field"
                          placeholder="username/ten-du-an"
                          value={ghForm.repo}
                          onChange={(e) => setGhForm({ ...ghForm, repo: e.target.value })}
                        />
                      </div>
                      <div style={{ marginBottom: '14px' }}>
                        <label className="field-label">Mã GitHub Token (PAT)</label>
                        <input
                          type="password"
                          className="input-field"
                          value={ghForm.token}
                          onChange={(e) => setGhForm({ ...ghForm, token: e.target.value })}
                        />
                      </div>
                      <button
                        type="button"
                        className="btn btn-outline"
                        onClick={() => handleSyncApi('github')}
                      >
                        Đẩy trực tiếp lên GitHub Issues
                      </button>
                    </div>
                  </div>
                )}

                {syncPlatform === 'trello' && (
                  <div>
                    <div style={{ marginBottom: '16px' }}>
                      <a href="/api/export/trello-json" className="btn btn-primary">
                        <Icon name="download" size={17} />
                        <span>Tải File Bảng Trello (.json) về máy ngay</span>
                      </a>
                    </div>
                    <div style={{ borderTop: '1px solid #E2E8F0', paddingTop: '16px', maxWidth: '520px' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.92rem', marginBottom: '12px' }}>
                        Hoặc tạo thẻ trực tiếp trên bảng Trello:
                      </div>
                      <div style={{ marginBottom: '10px' }}>
                        <label className="field-label">Trello API Key</label>
                        <input
                          type="text"
                          className="input-field"
                          value={trelloForm.api_key}
                          onChange={(e) => setTrelloForm({ ...trelloForm, api_key: e.target.value })}
                        />
                      </div>
                      <div style={{ marginBottom: '10px' }}>
                        <label className="field-label">Trello Token</label>
                        <input
                          type="password"
                          className="input-field"
                          value={trelloForm.token}
                          onChange={(e) => setTrelloForm({ ...trelloForm, token: e.target.value })}
                        />
                      </div>
                      <div style={{ marginBottom: '14px' }}>
                        <label className="field-label">Mã cột Trello (List ID)</label>
                        <input
                          type="text"
                          className="input-field"
                          value={trelloForm.list_id}
                          onChange={(e) => setTrelloForm({ ...trelloForm, list_id: e.target.value })}
                        />
                      </div>
                      <button
                        type="button"
                        className="btn btn-outline"
                        onClick={() => handleSyncApi('trello')}
                      >
                        Đẩy trực tiếp lên Trello Board
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="step-footer">
              <button type="button" className="btn btn-outline" onClick={() => setStep(2)}>
                ← Quay lại Bước 2 (Kiểm tra &amp; Sửa lại các câu yêu cầu)
              </button>
              <button type="button" className="btn btn-outline" onClick={() => setStep(1)}>
                Phân tích một tài liệu mới khác
              </button>
            </div>
          </div>
        )}
      </main>

      {/* ====================================================================
          OPTIONAL AI SETTINGS MODAL (HIDDEN UNLESS USER CLICKS "TÙY CHỌN AI")
          ==================================================================== */}
      {showAiModal && (
        <div className="modal-backdrop" onClick={() => setShowAiModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '16px',
              }}
            >
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                  Tùy chọn Chế độ Phân tích &amp; Kết nối AI
                </h3>
                <p style={{ fontSize: '0.82rem', color: '#64748B' }}>
                  Mặc định hệ thống đã chạy tự động trên máy mà không cần bạn nhập khóa API
                </p>
              </div>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '0.8rem' }}
                onClick={() => setShowAiModal(false)}
              >
                Đóng
              </button>
            </div>

            <div style={{ marginBottom: '14px' }}>
              <label className="field-label">Chế độ xử lý</label>
              <select
                className="select-field"
                value={provider}
                onChange={(e) => handleProviderChange(e.target.value)}
              >
                <option value="local_nlp">
                  Chạy tự động trên máy (Mặc định - Không cần nhập API Key)
                </option>
                <option value="groq">Kết nối Groq Cloud AI (Cần nhập API Key)</option>
                <option value="gemini">Kết nối Google Gemini AI (Cần nhập API Key)</option>
                <option value="openrouter">Kết nối OpenRouter AI (Cần nhập API Key)</option>
                <option value="ollama">Kết nối Ollama trên máy (Cổng 11434)</option>
              </select>
            </div>

            {provider !== 'local_nlp' && provider !== 'ollama' && (
              <div style={{ marginBottom: '14px' }}>
                <label className="field-label">
                  Nhập mã khóa API Key ({provider.toUpperCase()})
                </label>
                <input
                  type="password"
                  className="input-field"
                  placeholder="Dán mã khóa API Key của bạn vào đây..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </div>
            )}

            {provider !== 'local_nlp' && (
              <div style={{ marginBottom: '14px' }}>
                <label className="field-label">Tên mô hình AI</label>
                <input
                  type="text"
                  className="input-field"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                />
              </div>
            )}

            <div style={{ textAlign: 'right', marginTop: '18px' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setShowAiModal(false)}
              >
                Lưu &amp; Quay lại
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          LIVE PROGRESS MODAL DURING ANALYSIS
          ==================================================================== */}
      {isAnalyzing && (
        <div className="modal-backdrop">
          <div className="modal-box">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A' }}>
                  Đang phân tích tài liệu của bạn...
                </div>
                <div style={{ fontSize: '0.85rem', color: '#64748B', marginTop: '2px' }}>
                  {jobMessage || 'Vui lòng đợi trong giây lát'}
                </div>
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '1.2rem',
                  fontWeight: 700,
                  color: '#2563EB',
                }}
              >
                {(elapsedMs / 1000).toFixed(1)}s
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

            {currentJobIdRef.current && (
              <div style={{ marginTop: '16px', textAlign: 'right' }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={handleCancelAnalysis}
                >
                  Hủy phân tích
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

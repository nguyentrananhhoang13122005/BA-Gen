import React, { useEffect, useMemo, useRef, useState } from 'react';

/**
 * Chia dòng nhãn Use Case cân đối theo chuẩn UML 2.5
 */
function wrapUseCaseText(text, maxChars = 24) {
  const clean = (text || '').trim();
  if (clean.length <= maxChars) return [clean];
  const words = clean.split(/\s+/);
  const lines = [];
  let current = '';

  words.forEach((word) => {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxChars) {
      current = candidate;
    } else {
      if (current) lines.push(current);
      current = word;
    }
  });
  if (current) lines.push(current);
  return lines.slice(0, 3);
}

/**
 * Tính bán kính Elip (rx, ry) vừa vặn với độ dài chữ bên trong
 */
function getEllipseRadii(name) {
  const lines = wrapUseCaseText(name, 24);
  const longest = Math.max(...lines.map((l) => l.length), 10);
  const rx = Math.max(98, Math.min(142, Math.round(longest * 3.9 + 30)));
  const ry = lines.length >= 3 ? 40 : lines.length === 2 ? 35 : 30;
  return { rx, ry, lines };
}

/**
 * Toán học giao điểm tia - Elip / Actor để đường nối luôn chạm đúng mép viền chuẩn StarUML / Draw.io
 */
function computePerimeterPoints(srcNode, dstNode) {
  const dx = dstNode.x - srcNode.x;
  const dy = dstNode.y - srcNode.y;
  const angle = Math.atan2(dy, dx);

  let x1 = srcNode.x;
  let y1 = srcNode.y;
  if (srcNode.kind === 'actor') {
    x1 = srcNode.x + Math.cos(angle) * 32;
    y1 = srcNode.y + Math.sin(angle) * 36;
  } else {
    const { rx, ry } = getEllipseRadii(srcNode.name);
    x1 = srcNode.x + (rx + 2) * Math.cos(angle);
    y1 = srcNode.y + (ry + 2) * Math.sin(angle);
  }

  const backAngle = angle + Math.PI;
  let x2 = dstNode.x;
  let y2 = dstNode.y;
  if (dstNode.kind === 'actor') {
    x2 = dstNode.x + Math.cos(backAngle) * 32;
    y2 = dstNode.y + Math.sin(backAngle) * 36;
  } else {
    const { rx, ry } = getEllipseRadii(dstNode.name);
    x2 = dstNode.x + (rx + 4) * Math.cos(backAngle);
    y2 = dstNode.y + (ry + 4) * Math.sin(backAngle);
  }

  return { x1, y1, x2, y2 };
}

/**
 * Làm sạch tên hệ thống hiển thị trên khung System Boundary
 */
function cleanSystemTitle(rawTitle) {
  if (!rawTitle) return 'Hệ thống Phần mềm';
  return rawTitle
    .replace(/\.docx$|\.txt$/i, '')
    .replace(/^Topic\s+\d+\s*[—\-:]\s*/i, '')
    .trim();
}

/**
 * Khởi tạo đồ thị UML 2.5 chuẩn từ danh sách User Stories
 */
function buildInitialGraph(userStories = [], projectName = 'Hệ thống Phần mềm') {
  const actorMap = new Map();
  const useCases = [];
  const links = [];

  userStories.forEach((us, idx) => {
    const roleName = (us.role || 'Business Analyst').trim();
    if (!actorMap.has(roleName)) {
      actorMap.set(roleName, {
        id: `actor_${actorMap.size + 1}`,
        name: roleName,
        x: 105,
        y: 160 + actorMap.size * 170,
      });
    }
    const actor = actorMap.get(roleName);
    const ucId = `uc_${idx + 1}`;
    const ucName = (us.puml_usecase_name || us.goal || `Use Case ${idx + 1}`).trim();

    useCases.push({
      id: ucId,
      code: `UC-${String(idx + 1).padStart(2, '0')}`,
      name: ucName,
      x: 0,
      y: 0,
    });

    links.push({
      id: `link_assoc_${idx + 1}`,
      from: actor.id,
      to: ucId,
      type: 'association',
    });
  });

  const actors = Array.from(actorMap.values());
  const count = useCases.length;

  // Bố cục 2 cột so le (Staggered Dual-Column UML Layout) để các đường nối từ Actor không bao giờ cắt đè lên Elip khác
  useCases.forEach((uc, idx) => {
    if (count <= 4) {
      uc.x = 560;
      uc.y = 125 + idx * 105;
    } else {
      const col = idx % 2;
      const row = Math.floor(idx / 2);
      uc.x = col === 0 ? 455 : 755;
      uc.y = 120 + row * 115 + (col === 1 ? 32 : 0);
    }
  });

  // Tự động nhận diện quan hệ <<include>> / <<extend>> hợp lý giữa các Use Case liên tiếp
  for (let i = 0; i < useCases.length - 1; i++) {
    const cur = useCases[i].name.toLowerCase();
    const nxt = useCases[i + 1].name.toLowerCase();
    if (
      (cur.includes('upload') && nxt.includes('split')) ||
      (cur.includes('split') && nxt.includes('classify')) ||
      (cur.includes('tải') && nxt.includes('tách')) ||
      (cur.includes('giỏ hàng') && nxt.includes('thanh toán'))
    ) {
      links.push({
        id: `link_inc_${i + 1}`,
        from: useCases[i].id,
        to: useCases[i + 1].id,
        type: 'include',
      });
    } else if (
      (cur.includes('classify') && nxt.includes('flag')) ||
      (cur.includes('flag') && nxt.includes('generate'))
    ) {
      links.push({
        id: `link_ext_${i + 1}`,
        from: useCases[i + 1].id,
        to: useCases[i].id,
        type: 'extend',
      });
    }
  }

  const maxUcY = useCases.length ? Math.max(...useCases.map((u) => u.y)) : 340;
  const totalH = Math.max(maxUcY + 115, actors.length * 165 + 110, 480);

  if (actors.length === 1) {
    actors[0].y = Math.round(totalH / 2);
  } else if (actors.length > 1) {
    const gap = Math.min(175, Math.max(130, (totalH - 140) / (actors.length - 1)));
    const topY = Math.round((totalH - gap * (actors.length - 1)) / 2);
    actors.forEach((a, i) => {
      a.y = topY + i * gap;
    });
  }

  return {
    systemTitle: cleanSystemTitle(projectName),
    actors,
    useCases,
    links,
  };
}

/**
 * Sinh mã chuẩn PlantUML 2.5 từ trạng thái đồ thị
 */
function generatePlantUmlFromGraph(graph) {
  const lines = [
    '@startuml',
    'left to right direction',
    'skinparam packageStyle rectangle',
    'skinparam shadowing false',
    'skinparam defaultFontName "Segoe UI"',
    'skinparam usecase {',
    '  BackgroundColor #F8FAFC',
    '  BorderColor #1E3A8A',
    '  BorderThickness 1.8',
    '  ArrowColor #334155',
    '}',
    'skinparam actor {',
    '  BackgroundColor #FFFFFF',
    '  BorderColor #0F172A',
    '  BorderThickness 1.8',
    '}',
    '',
  ];

  graph.actors.forEach((a) => {
    const safeName = a.name.replace(/"/g, "'");
    lines.push(`actor "${safeName}" as ${a.id}`);
  });

  lines.push('');
  const safeSys = (graph.systemTitle || 'System').replace(/"/g, "'");
  lines.push(`rectangle "${safeSys}" {`);
  graph.useCases.forEach((uc) => {
    const safeUc = uc.name.replace(/"/g, "'");
    lines.push(`  usecase "${safeUc}" as ${uc.id}`);
  });
  lines.push('}');
  lines.push('');

  graph.links.forEach((lnk) => {
    if (lnk.type === 'include') {
      lines.push(`${lnk.from} ..> ${lnk.to} : <<include>>`);
    } else if (lnk.type === 'extend') {
      lines.push(`${lnk.from} ..> ${lnk.to} : <<extend>>`);
    } else {
      lines.push(`${lnk.from} -- ${lnk.to}`);
    }
  });

  lines.push('@enduml');
  return lines.join('\n');
}

export default function UmlCanvasStudio({
  userStories = [],
  projectName = 'Hệ thống Phần mềm',
  initialPlantUmlCode = '',
}) {
  const [graph, setGraph] = useState(() => buildInitialGraph(userStories, projectName));
  const [selectedItem, setSelectedItem] = useState(null); // { kind: 'actor' | 'uc' | 'link', id: string }
  const [dragging, setDragging] = useState(null);
  const [connectMode, setConnectMode] = useState(null); // null | { step: 'pick-from' | 'pick-to', fromId?: string, type: 'association' | 'include' | 'extend' }
  const [zoom, setZoom] = useState(1);
  const [mode, setMode] = useState('canvas');
  const [pumlText, setPumlText] = useState(initialPlantUmlCode);
  const [syncMessage, setSyncMessage] = useState('');

  const svgRef = useRef(null);

  useEffect(() => {
    const nextGraph = buildInitialGraph(userStories, projectName);
    setGraph(nextGraph);
    setPumlText(generatePlantUmlFromGraph(nextGraph));
    setSelectedItem(null);
    setConnectMode(null);
  }, [userStories, projectName]);

  const syncToBackend = (updatedGraph) => {
    const code = generatePlantUmlFromGraph(updatedGraph);
    setPumlText(code);
    fetch('/api/diagram/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plantuml_code: code }),
    }).catch(() => {});
  };

  const canvasWidth = 980;
  const canvasHeight = useMemo(() => {
    const maxA = graph.actors.length ? Math.max(...graph.actors.map((a) => a.y)) : 300;
    const maxU = graph.useCases.length ? Math.max(...graph.useCases.map((u) => u.y)) : 300;
    return Math.max(maxA + 125, maxU + 115, 500);
  }, [graph]);

  const getSvgCoords = (clientX, clientY) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    return {
      x: ((clientX - rect.left) / rect.width) * canvasWidth,
      y: ((clientY - rect.top) / rect.height) * canvasHeight,
    };
  };

  // Xử lý click / kéo nút trên bản vẽ
  const handlePointerDownNode = (e, kind, item) => {
    e.stopPropagation();

    // Nếu đang ở chế độ Kẻ Đường Nối Trực Tiếp
    if (connectMode) {
      if (connectMode.step === 'pick-from') {
        setConnectMode({ ...connectMode, step: 'pick-to', fromId: item.id });
      } else if (connectMode.step === 'pick-to') {
        if (connectMode.fromId && connectMode.fromId !== item.id) {
          const exists = graph.links.some(
            (l) => l.from === connectMode.fromId && l.to === item.id
          );
          if (!exists) {
            const nextGraph = {
              ...graph,
              links: [
                ...graph.links,
                {
                  id: `link_${Date.now()}`,
                  from: connectMode.fromId,
                  to: item.id,
                  type: connectMode.type,
                },
              ],
            };
            setGraph(nextGraph);
            syncToBackend(nextGraph);
          }
        }
        setConnectMode(null);
      }
      return;
    }

    const pt = getSvgCoords(e.clientX, e.clientY);
    setSelectedItem({ kind, id: item.id });
    setDragging({
      kind,
      id: item.id,
      offsetX: pt.x - item.x,
      offsetY: pt.y - item.y,
    });
  };

  const handlePointerMoveCanvas = (e) => {
    if (!dragging) return;
    const pt = getSvgCoords(e.clientX, e.clientY);
    // Snap-to-grid 8px cho bản vẽ thẳng hàng sắc nét
    const rawX = pt.x - dragging.offsetX;
    const rawY = pt.y - dragging.offsetY;
    const snappedX = Math.round(rawX / 8) * 8;
    const snappedY = Math.round(rawY / 8) * 8;

    const nextX = Math.max(70, Math.min(canvasWidth - 110, snappedX));
    const nextY = Math.max(85, Math.min(canvasHeight - 65, snappedY));

    setGraph((prev) => {
      if (dragging.kind === 'actor') {
        return {
          ...prev,
          actors: prev.actors.map((a) =>
            a.id === dragging.id ? { ...a, x: nextX, y: nextY } : a
          ),
        };
      }
      return {
        ...prev,
        useCases: prev.useCases.map((u) =>
          u.id === dragging.id ? { ...u, x: nextX, y: nextY } : u
        ),
      };
    });
  };

  const handlePointerUpCanvas = () => {
    if (dragging) {
      setDragging(null);
      syncToBackend(graph);
    }
  };

  const handleAddActor = () => {
    const idx = graph.actors.length + 1;
    const newActor = {
      id: `actor_${Date.now()}`,
      name: `Actor ${idx}`,
      x: 105,
      y: Math.min(canvasHeight - 80, 140 + (idx - 1) * 140),
    };
    const nextGraph = { ...graph, actors: [...graph.actors, newActor] };
    setGraph(nextGraph);
    setSelectedItem({ kind: 'actor', id: newActor.id });
    syncToBackend(nextGraph);
  };

  const handleAddUseCase = () => {
    const idx = graph.useCases.length + 1;
    const firstActor = graph.actors[0];
    const newUc = {
      id: `uc_${Date.now()}`,
      code: `UC-${String(idx).padStart(2, '0')}`,
      name: `New Use Case ${idx}`,
      x: idx % 2 === 1 ? 460 : 755,
      y: 125 + Math.floor((idx - 1) / 2) * 110,
    };
    const nextLinks = firstActor
      ? [
          ...graph.links,
          {
            id: `link_${Date.now()}`,
            from: firstActor.id,
            to: newUc.id,
            type: 'association',
          },
        ]
      : graph.links;

    const nextGraph = {
      ...graph,
      useCases: [...graph.useCases, newUc],
      links: nextLinks,
    };
    setGraph(nextGraph);
    setSelectedItem({ kind: 'uc', id: newUc.id });
    syncToBackend(nextGraph);
  };

  const handleRenameSelectedNode = (newName) => {
    if (!selectedItem || selectedItem.kind === 'link') return;
    const nextGraph =
      selectedItem.kind === 'actor'
        ? {
            ...graph,
            actors: graph.actors.map((a) =>
              a.id === selectedItem.id ? { ...a, name: newName } : a
            ),
          }
        : {
            ...graph,
            useCases: graph.useCases.map((u) =>
              u.id === selectedItem.id ? { ...u, name: newName } : u
            ),
          };
    setGraph(nextGraph);
    syncToBackend(nextGraph);
  };

  const handleChangeSelectedLinkType = (newType) => {
    if (!selectedItem || selectedItem.kind !== 'link') return;
    const nextGraph = {
      ...graph,
      links: graph.links.map((l) =>
        l.id === selectedItem.id ? { ...l, type: newType } : l
      ),
    };
    setGraph(nextGraph);
    syncToBackend(nextGraph);
  };

  const handleDeleteSelected = () => {
    if (!selectedItem) return;
    const id = selectedItem.id;
    const nextGraph = {
      ...graph,
      actors: graph.actors.filter((a) => a.id !== id),
      useCases: graph.useCases.filter((u) => u.id !== id),
      links: graph.links.filter((l) => l.id !== id && l.from !== id && l.to !== id),
    };
    setGraph(nextGraph);
    setSelectedItem(null);
    syncToBackend(nextGraph);
  };

  const handleResetLayout = () => {
    const fresh = buildInitialGraph(userStories, projectName);
    setGraph(fresh);
    setSelectedItem(null);
    setConnectMode(null);
    syncToBackend(fresh);
  };

  const handleDownloadSvg = () => {
    const svgEl = svgRef.current;
    if (!svgEl) return;
    let source = new XMLSerializer().serializeToString(svgEl);
    if (!source.includes('xmlns="http://www.w3.org/2000/svg"')) {
      source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${graph.systemTitle}_UseCase_UML.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPng = () => {
    const svgEl = svgRef.current;
    if (!svgEl) return;
    let source = new XMLSerializer().serializeToString(svgEl);
    if (!source.includes('xmlns="http://www.w3.org/2000/svg"')) {
      source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    const svgBlob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);
    const img = new Image();
    img.onload = () => {
      const scale = 2;
      const canvas = document.createElement('canvas');
      canvas.width = canvasWidth * scale;
      canvas.height = canvasHeight * scale;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      canvas.toBlob((pngBlob) => {
        if (!pngBlob) return;
        const pngUrl = URL.createObjectURL(pngBlob);
        const a = document.createElement('a');
        a.href = pngUrl;
        a.download = `${graph.systemTitle}_UseCase_UML.png`;
        a.click();
        URL.revokeObjectURL(pngUrl);
      }, 'image/png');
    };
    img.src = url;
  };

  const nodeMap = useMemo(() => {
    const m = {};
    graph.actors.forEach((a) => {
      m[a.id] = { ...a, kind: 'actor' };
    });
    graph.useCases.forEach((u) => {
      m[u.id] = { ...u, kind: 'uc' };
    });
    return m;
  }, [graph]);

  const activeNodeObj = useMemo(() => {
    if (!selectedItem) return null;
    if (selectedItem.kind === 'link') {
      return graph.links.find((l) => l.id === selectedItem.id) || null;
    }
    return nodeMap[selectedItem.id] || null;
  }, [selectedItem, graph, nodeMap]);

  return (
    <div className="card" style={{ marginBottom: '22px' }}>
      {/* HEADER BAR */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
          paddingBottom: '14px',
          marginBottom: '14px',
          borderBottom: '1px solid #E2E8F0',
        }}
      >
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A' }}>
            Trình Vẽ Sơ đồ UML 2.5 Use Case Tương tác (Chuẩn StarUML / Draw.io)
          </h3>
          <p style={{ fontSize: '0.84rem', color: '#64748B' }}>
            Kéo-thả các phần tử, bấm vào bất kỳ hình hoặc đường nối nào để chỉnh sửa trực tiếp trên bản vẽ
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className={`filter-tab ${mode === 'canvas' ? 'active' : ''}`}
            onClick={() => setMode('canvas')}
          >
            Bản vẽ UML Tương tác
          </button>
          <button
            type="button"
            className={`filter-tab ${mode === 'code' ? 'active' : ''}`}
            onClick={() => setMode('code')}
          >
            Mã PlantUML (@startuml)
          </button>
        </div>
      </div>

      {mode === 'canvas' && (
        <div>
          {/* TOOLBAR: ADD NODES, DRAW ARROWS ON CANVAS, AUTO-LAYOUT, EXPORT */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '10px',
              flexWrap: 'wrap',
              background: '#F8FAFC',
              border: '1px solid #CBD5E1',
              borderRadius: '10px',
              padding: '10px 14px',
              marginBottom: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '7px 12px', fontSize: '0.83rem', background: '#FFFFFF' }}
                onClick={handleAddActor}
              >
                + Thêm Actor
              </button>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '7px 12px', fontSize: '0.83rem', background: '#FFFFFF' }}
                onClick={handleAddUseCase}
              >
                + Thêm Use Case
              </button>

              {/* NÚT KẺ ĐƯỜNG NỐI TRỰC TIẾP TRÊN HÌNH */}
              <button
                type="button"
                className={`btn ${connectMode ? 'btn-primary' : 'btn-outline'}`}
                style={{
                  padding: '7px 12px',
                  fontSize: '0.83rem',
                  background: connectMode ? '#2563EB' : '#FFFFFF',
                }}
                onClick={() =>
                  setConnectMode(
                    connectMode
                      ? null
                      : { step: 'pick-from', type: 'association' }
                  )
                }
              >
                {connectMode ? '✕ Hủy kẻ đường nối' : '⎯ Nối dây trực tiếp trên hình'}
              </button>

              {connectMode && (
                <select
                  className="select-field"
                  style={{ width: 'auto', padding: '6px 10px', fontSize: '0.82rem' }}
                  value={connectMode.type}
                  onChange={(e) => setConnectMode({ ...connectMode, type: e.target.value })}
                >
                  <option value="association">Kiểu: Đường nối Actor — Use Case</option>
                  <option value="include">Kiểu: --«include»--&gt;</option>
                  <option value="extend">Kiểu: --«extend»--&gt;</option>
                </select>
              )}

              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '7px 12px', fontSize: '0.82rem', background: '#FFFFFF' }}
                onClick={handleResetLayout}
              >
                Căn chỉnh lại bố cục
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '6px 10px', fontSize: '0.8rem', background: '#FFFFFF' }}
                onClick={() => setZoom((z) => Math.max(0.75, Number((z - 0.1).toFixed(2))))}
              >
                -
              </button>
              <span style={{ fontSize: '0.82rem', fontWeight: 700, minWidth: '42px', textAlign: 'center' }}>
                {Math.round(zoom * 100)}%
              </span>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '6px 10px', fontSize: '0.8rem', background: '#FFFFFF' }}
                onClick={() => setZoom((z) => Math.min(1.35, Number((z + 0.1).toFixed(2))))}
              >
                +
              </button>
              <button
                type="button"
                className="btn btn-primary"
                style={{ padding: '7px 14px', fontSize: '0.83rem' }}
                onClick={handleDownloadPng}
              >
                Tải Ảnh Sơ đồ (.png)
              </button>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '7px 12px', fontSize: '0.82rem', background: '#FFFFFF' }}
                onClick={handleDownloadSvg}
              >
                Tải Vector (.svg)
              </button>
            </div>
          </div>

          {/* HƯỚNG DẪN KHI ĐANG BẬT CHẾ ĐỘ KẺ ĐƯỜNG NỐI TRỰC TIẾP */}
          {connectMode && (
            <div
              style={{
                background: '#EFF6FF',
                border: '1px solid #93C5FD',
                color: '#1E3A8A',
                padding: '9px 14px',
                borderRadius: '8px',
                fontSize: '0.86rem',
                fontWeight: 600,
                marginBottom: '12px',
              }}
            >
              {connectMode.step === 'pick-from'
                ? '👉 Bước 1: Hãy bấm chuột vào hình Bắt đầu (Actor hoặc Use Case) ngay trên bản vẽ bên dưới...'
                : '👉 Bước 2: Bây giờ hãy bấm chuột vào hình Use Case Đích để hoàn tất nối dây!'}
            </div>
          )}

          {/* THANH CHỈNH SỬA PHẦN TỬ ĐANG CHỌN (NODE HOẶC ĐƯỜNG NỐI) */}
          {selectedItem && activeNodeObj && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
                flexWrap: 'wrap',
                background: '#F0FDF4',
                border: '1px solid #86EFAC',
                borderRadius: '9px',
                padding: '10px 14px',
                marginBottom: '12px',
              }}
            >
              {selectedItem.kind !== 'link' ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '260px' }}>
                  <span className="badge badge-num">
                    {selectedItem.kind === 'actor' ? 'Actor' : activeNodeObj.code}
                  </span>
                  <input
                    type="text"
                    className="input-field"
                    style={{ padding: '6px 12px', fontSize: '0.9rem', maxWidth: '460px' }}
                    value={activeNodeObj.name}
                    onChange={(e) => handleRenameSelectedNode(e.target.value)}
                  />
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  <span className="badge badge-num">Đang chọn Đường nối</span>
                  <select
                    className="select-field"
                    style={{ width: 'auto', padding: '6px 12px', fontSize: '0.85rem' }}
                    value={activeNodeObj.type}
                    onChange={(e) => handleChangeSelectedLinkType(e.target.value)}
                  >
                    <option value="association">Association (Đường thẳng liền)</option>
                    <option value="include">«include» (Nét đứt có mũi tên)</option>
                    <option value="extend">«extend» (Nét đứt mở rộng)</option>
                  </select>
                </div>
              )}

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{
                    padding: '6px 12px',
                    fontSize: '0.82rem',
                    color: '#B91C1C',
                    borderColor: '#FCA5A5',
                    background: '#FEF2F2',
                  }}
                  onClick={handleDeleteSelected}
                >
                  Xóa phần tử này
                </button>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ padding: '6px 12px', fontSize: '0.82rem', background: '#FFFFFF' }}
                  onClick={() => setSelectedItem(null)}
                >
                  Đóng
                </button>
              </div>
            </div>
          )}

          {/* BẢNG VẼ VECTOR UML 2.5 CHUẨN KỸ THUẬT */}
          <div
            style={{
              background: '#F1F5F9',
              border: '1px solid #CBD5E1',
              borderRadius: '10px',
              padding: '16px',
              overflow: 'auto',
              maxHeight: '680px',
            }}
          >
            <svg
              ref={svgRef}
              viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
              width={Math.round(canvasWidth * zoom)}
              height={Math.round(canvasHeight * zoom)}
              style={{
                display: 'block',
                margin: '0 auto',
                background: '#FFFFFF',
                borderRadius: '6px',
                boxShadow: '0 2px 10px rgba(15, 23, 42, 0.08)',
                userSelect: 'none',
                cursor: connectMode ? 'crosshair' : dragging ? 'grabbing' : 'default',
              }}
              onPointerMove={handlePointerMoveCanvas}
              onPointerUp={handlePointerUpCanvas}
              onPointerLeave={handlePointerUpCanvas}
              onClick={() => setSelectedItem(null)}
            >
              <defs>
                {/* Mũi tên mở chuẩn UML 2.5 cho <<include>> & <<extend>> */}
                <marker
                  id="uml-open-arrow"
                  viewBox="0 0 12 12"
                  refX="10"
                  refY="6"
                  markerWidth="9"
                  markerHeight="9"
                  orient="auto-start-reverse"
                >
                  <path
                    d="M 1 2 L 10 6 L 1 10"
                    fill="none"
                    stroke="#1E293B"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </marker>

                {/* Bóng đổ nhẹ chuẩn StarUML cho Elip Use Case */}
                <filter id="uml-drop-shadow" x="-10%" y="-10%" width="125%" height="125%">
                  <feDropShadow dx="1" dy="2" stdDeviation="2" floodColor="#0F172A" floodOpacity="0.08" />
                </filter>

                <linearGradient id="uc-fill" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#FFFFFF" />
                  <stop offset="100%" stopColor="#EFF6FF" />
                </linearGradient>

                <linearGradient id="uc-fill-selected" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#EFF6FF" />
                  <stop offset="100%" stopColor="#DBEAFE" />
                </linearGradient>
              </defs>

              {/* KHUNG SYSTEM BOUNDARY CHUẨN UML 2.5 */}
              <rect
                x="255"
                y="28"
                width="695"
                height={canvasHeight - 56}
                rx="4"
                fill="#FAFAFC"
                stroke="#1E293B"
                strokeWidth="1.8"
              />
              {/* Thanh tiêu đề khung hệ thống chuẩn UML */}
              <line
                x1="255"
                y1="66"
                x2="950"
                y2="66"
                stroke="#CBD5E1"
                strokeWidth="1.2"
              />
              <text
                x="602"
                y="45"
                textAnchor="middle"
                fill="#64748B"
                fontFamily="JetBrains Mono, monospace"
                fontSize="10.5"
              >
                «system»
              </text>
              <text
                x="602"
                y="60"
                textAnchor="middle"
                fill="#0F172A"
                fontFamily="Be Vietnam Pro, Segoe UI, sans-serif"
                fontSize="13.5"
                fontWeight="700"
              >
                {graph.systemTitle}
              </text>

              {/* VẼ CÁC ĐƯỜNG NỐI QUAN HỆ (TÍNH GIAO ĐIỂM VIỀN CHÍNH XÁC) */}
              {graph.links.map((lnk) => {
                const src = nodeMap[lnk.from];
                const dst = nodeMap[lnk.to];
                if (!src || !dst) return null;

                const { x1, y1, x2, y2 } = computePerimeterPoints(src, dst);
                const midX = (x1 + x2) / 2;
                const midY = (y1 + y2) / 2;
                const isDep = lnk.type === 'include' || lnk.type === 'extend';
                const isSelectedLink =
                  selectedItem?.kind === 'link' && selectedItem?.id === lnk.id;

                return (
                  <g
                    key={lnk.id}
                    style={{ cursor: 'pointer' }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedItem({ kind: 'link', id: lnk.id });
                    }}
                  >
                    {/* Vùng đệm trong suốt giúp click chọn đường nối dễ dàng */}
                    <line
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="transparent"
                      strokeWidth="12"
                    />
                    <line
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke={isSelectedLink ? '#2563EB' : '#1E293B'}
                      strokeWidth={isSelectedLink ? '2.5' : '1.6'}
                      strokeDasharray={isDep ? '6 4' : 'none'}
                      markerEnd={isDep ? 'url(#uml-open-arrow)' : undefined}
                    />
                    {isDep && (
                      <g transform={`translate(${midX}, ${midY})`}>
                        <rect
                          x="-36"
                          y="-10"
                          width="72"
                          height="18"
                          rx="4"
                          fill="#FFFFFF"
                          stroke="#CBD5E1"
                          strokeWidth="1"
                        />
                        <text
                          x="0"
                          y="3"
                          textAnchor="middle"
                          fill="#1E3A8A"
                          fontFamily="JetBrains Mono, monospace"
                          fontSize="10.5"
                          fontWeight="600"
                        >
                          {`«${lnk.type}»`}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}

              {/* VẼ TÁC NHÂN (TEXTBOOK UML 2.5 STICK FIGURE ACTOR) */}
              {graph.actors.map((actor) => {
                const isSel =
                  (selectedItem?.kind === 'actor' && selectedItem?.id === actor.id) ||
                  connectMode?.fromId === actor.id;
                const actorLines = wrapUseCaseText(actor.name, 20);

                return (
                  <g
                    key={actor.id}
                    transform={`translate(${actor.x}, ${actor.y})`}
                    style={{ cursor: connectMode ? 'crosshair' : 'grab' }}
                    onPointerDown={(e) => handlePointerDownNode(e, 'actor', actor)}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {isSel && (
                      <rect
                        x="-56"
                        y="-42"
                        width="112"
                        height="108"
                        rx="6"
                        fill="rgba(37, 99, 235, 0.06)"
                        stroke="#2563EB"
                        strokeWidth="1.5"
                        strokeDasharray="4 3"
                      />
                    )}

                    {/* Đầu hình người chuẩn UML */}
                    <circle
                      cx="0"
                      cy="-22"
                      r="10.5"
                      fill="#FFFFFF"
                      stroke="#0F172A"
                      strokeWidth="2"
                    />
                    {/* Thân */}
                    <line x1="0" y1="-11.5" x2="0" y2="12" stroke="#0F172A" strokeWidth="2" />
                    {/* Hai tay ngang */}
                    <line x1="-16" y1="-2" x2="16" y2="-2" stroke="#0F172A" strokeWidth="2" />
                    {/* Hai chân */}
                    <line x1="0" y1="12" x2="-13" y2="31" stroke="#0F172A" strokeWidth="2" />
                    <line x1="0" y1="12" x2="13" y2="31" stroke="#0F172A" strokeWidth="2" />

                    {/* Nhãn tên Actor chuẩn sách giáo khoa UML bên dưới chân */}
                    {actorLines.map((ln, idx) => (
                      <text
                        key={idx}
                        x="0"
                        y={48 + idx * 15}
                        textAnchor="middle"
                        fill="#0F172A"
                        fontFamily="Be Vietnam Pro, Segoe UI, sans-serif"
                        fontSize="12.5"
                        fontWeight="700"
                      >
                        {ln}
                      </text>
                    ))}
                  </g>
                );
              })}

              {/* VẼ CA SỬ DỤNG (AUTO-SIZED TEXTBOOK UML 2.5 USE CASE ELLIPSES) */}
              {graph.useCases.map((uc) => {
                const isSel =
                  (selectedItem?.kind === 'uc' && selectedItem?.id === uc.id) ||
                  connectMode?.fromId === uc.id;
                const { rx, ry, lines } = getEllipseRadii(uc.name);
                const startTextY = -((lines.length - 1) * 15) / 2 + 4;

                return (
                  <g
                    key={uc.id}
                    transform={`translate(${uc.x}, ${uc.y})`}
                    style={{ cursor: connectMode ? 'crosshair' : 'grab' }}
                    onPointerDown={(e) => handlePointerDownNode(e, 'uc', uc)}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ellipse
                      cx="0"
                      cy="0"
                      rx={rx}
                      ry={ry}
                      fill={isSel ? 'url(#uc-fill-selected)' : 'url(#uc-fill)'}
                      stroke={isSel ? '#2563EB' : '#1E3A8A'}
                      strokeWidth={isSel ? '2.4' : '1.75'}
                      filter="url(#uml-drop-shadow)"
                    />

                    {lines.map((ln, idx) => (
                      <text
                        key={idx}
                        x="0"
                        y={startTextY + idx * 15}
                        textAnchor="middle"
                        fill="#0F172A"
                        fontFamily="Be Vietnam Pro, Segoe UI, sans-serif"
                        fontSize="12.2"
                        fontWeight="600"
                      >
                        {ln}
                      </text>
                    ))}
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      )}

      {/* TAB 2: PLANTUML SOURCE CODE */}
      {mode === 'code' && (
        <div>
          <textarea
            className="textarea-field"
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.86rem',
              minHeight: '260px',
              background: '#0F172A',
              color: '#E2E8F0',
            }}
            value={pumlText}
            onChange={(e) => setPumlText(e.target.value)}
          />
          <div
            style={{
              marginTop: '12px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span style={{ color: '#15803D', fontSize: '0.85rem', fontWeight: 600 }}>
              {syncMessage}
            </span>
            <div style={{ display: 'flex', gap: '10px' }}>
              <a
                href="/api/export/diagram-puml"
                download={`${graph.systemTitle}_usecase.puml`}
                className="btn btn-outline"
              >
                Tải File PlantUML (.puml)
              </a>
              <button
                type="button"
                className="btn btn-primary"
                onClick={async () => {
                  await fetch('/api/diagram/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plantuml_code: pumlText }),
                  });
                  setSyncMessage('✓ Đã cập nhật mã PlantUML!');
                }}
              >
                Lưu mã PlantUML
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

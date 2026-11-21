import React, { useEffect, useMemo, useRef, useState } from 'react';

/**
 * Chia dòng văn bản tiếng Việt để hiển thị gọn bên trong hình Elip Use Case
 */
function wrapLabel(text, maxCharsPerLine = 24) {
  const words = (text || '').trim().split(/\s+/);
  const lines = [];
  let current = '';

  words.forEach((w) => {
    if ((current + ' ' + w).trim().length <= maxCharsPerLine) {
      current = (current + ' ' + w).trim();
    } else {
      if (current) lines.push(current);
      current = w;
    }
  });
  if (current) lines.push(current);
  return lines.slice(0, 3);
}

/**
 * Tạo bố cục tọa độ tự động chuẩn UML 2.5 từ danh sách User Stories
 */
function buildInitialGraph(userStories = [], projectName = 'Hệ thống Phần mềm') {
  const actorMap = new Map();
  const useCases = [];
  const links = [];

  userStories.forEach((us, idx) => {
    const roleName = (us.role || 'Người dùng').trim();
    if (!actorMap.has(roleName)) {
      actorMap.set(roleName, {
        id: `actor_${actorMap.size + 1}`,
        name: roleName,
        x: 115,
        y: 130 + actorMap.size * 145,
      });
    }
    const actor = actorMap.get(roleName);
    const ucId = `uc_${idx + 1}`;
    const ucName = (us.puml_usecase_name || us.goal || `Chức năng ${idx + 1}`).trim();

    useCases.push({
      id: ucId,
      code: us.story_id || `UC-${idx + 1}`,
      name: ucName,
      x: 0,
      y: 0,
    });

    links.push({
      id: `link_${idx + 1}`,
      from: actor.id,
      to: ucId,
      type: 'association', // 'association' | 'include' | 'extend'
    });
  });

  const actors = Array.from(actorMap.values());
  const useTwoCols = useCases.length > 5;

  useCases.forEach((uc, idx) => {
    if (useTwoCols) {
      const col = idx % 2;
      const row = Math.floor(idx / 2);
      uc.x = col === 0 ? 450 : 740;
      uc.y = 125 + row * 105;
    } else {
      uc.x = 560;
      uc.y = 125 + idx * 100;
    }
  });

  // Căn giữa dọc cho danh sách Actor theo chiều cao của Use Cases
  const maxUcY = useCases.length > 0 ? Math.max(...useCases.map((u) => u.y)) : 320;
  const totalHeight = Math.max(maxUcY + 120, actors.length * 145 + 100, 460);

  if (actors.length > 0) {
    const spacing = Math.min(150, Math.max(115, (totalHeight - 120) / Math.max(actors.length, 1)));
    const startY = Math.max(120, (totalHeight - (actors.length - 1) * spacing) / 2);
    actors.forEach((a, i) => {
      a.y = Math.round(startY + i * spacing);
    });
  }

  return {
    systemTitle: projectName || 'Hệ thống Phần mềm',
    actors,
    useCases,
    links,
  };
}

/**
 * Sinh mã chuẩn PlantUML từ trạng thái đồ thị trên Canvas
 */
function generatePlantUmlFromGraph(graph) {
  const lines = [
    '@startuml',
    'left to right direction',
    'skinparam packageStyle rectangle',
    'skinparam shadowing false',
    'skinparam usecase {',
    '  BackgroundColor #EFF6FF',
    '  BorderColor #1D4ED8',
    '  ArrowColor #334155',
    '}',
    'skinparam actor {',
    '  BackgroundColor #0F766E',
    '  BorderColor #0F172A',
    '}',
    '',
  ];

  graph.actors.forEach((a) => {
    const safeName = a.name.replace(/"/g, "'");
    lines.push(`actor "${safeName}" as ${a.id}`);
  });

  lines.push('');
  const safeSys = (graph.systemTitle || 'Hệ thống').replace(/"/g, "'");
  lines.push(`rectangle "Hệ thống: ${safeSys}" {`);
  graph.useCases.forEach((uc) => {
    const safeUc = uc.name.replace(/"/g, "'");
    lines.push(`  usecase "${safeUc}\\n(${uc.code})" as ${uc.id}`);
  });
  lines.push('}');
  lines.push('');

  graph.links.forEach((lnk) => {
    if (lnk.type === 'include') {
      lines.push(`${lnk.from} ..> ${lnk.to} : <<include>>`);
    } else if (lnk.type === 'extend') {
      lines.push(`${lnk.from} ..> ${lnk.to} : <<extend>>`);
    } else {
      lines.push(`${lnk.from} --> ${lnk.to}`);
    }
  });

  lines.push('@enduml');
  return lines.join('\n');
}

export default function UmlCanvasStudio({
  userStories = [],
  projectName = 'Hệ thống Phần mềm',
  initialPlantUmlCode = '',
  hasKrokiImage = false,
}) {
  const [graph, setGraph] = useState(() => buildInitialGraph(userStories, projectName));
  const [selectedNode, setSelectedNode] = useState(null); // { kind: 'actor' | 'uc', id: string }
  const [dragging, setDragging] = useState(null); // { kind, id, offsetX, offsetY }
  const [zoom, setZoom] = useState(1);
  const [mode, setMode] = useState('canvas'); // 'canvas' | 'code'
  const [pumlText, setPumlText] = useState(initialPlantUmlCode);
  const [syncMessage, setSyncMessage] = useState('');

  // Form thêm nhanh quan hệ nối dây
  const [newLinkFrom, setNewLinkFrom] = useState('');
  const [newLinkTo, setNewLinkTo] = useState('');
  const [newLinkType, setNewLinkType] = useState('association');

  const svgRef = useRef(null);

  // Khởi tạo lại đồ thị khi danh sách userStories thay đổi
  useEffect(() => {
    const nextGraph = buildInitialGraph(userStories, projectName);
    setGraph(nextGraph);
    setPumlText(initialPlantUmlCode || generatePlantUmlFromGraph(nextGraph));
    setSelectedNode(null);
  }, [userStories, projectName]);

  // Tự động đồng bộ mã PlantUML mỗi khi người dùng kéo thả hoặc thêm/sửa/xóa nút trên Canvas
  const syncGraphToPlantUml = (updatedGraph) => {
    const code = generatePlantUmlFromGraph(updatedGraph);
    setPumlText(code);
    fetch('/api/diagram/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plantuml_code: code }),
    }).catch(() => {});
  };

  // Tính kích thước khung vẽ SVG tự động theo tọa độ các phần tử
  const canvasHeight = useMemo(() => {
    const maxActorY = graph.actors.length ? Math.max(...graph.actors.map((a) => a.y)) : 300;
    const maxUcY = graph.useCases.length ? Math.max(...graph.useCases.map((u) => u.y)) : 300;
    return Math.max(maxActorY + 130, maxUcY + 130, 500);
  }, [graph]);

  const canvasWidth = 960;

  // Chuyển đổi tọa độ chuột màn hình sang tọa độ bên trong SVG
  const getSvgCoords = (clientX, clientY) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    const scaleX = canvasWidth / rect.width;
    const scaleY = canvasHeight / rect.height;
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    };
  };

  const handlePointerDownNode = (e, kind, item) => {
    e.stopPropagation();
    const pt = getSvgCoords(e.clientX, e.clientY);
    setSelectedNode({ kind, id: item.id });
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
    const nextX = Math.max(65, Math.min(canvasWidth - 95, Math.round(pt.x - dragging.offsetX)));
    const nextY = Math.max(85, Math.min(canvasHeight - 60, Math.round(pt.y - dragging.offsetY)));

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
      syncGraphToPlantUml(graph);
    }
  };

  // Thêm Người dùng (Actor) mới trực tiếp trên Web
  const handleAddActor = () => {
    const nextIdx = graph.actors.length + 1;
    const newActor = {
      id: `actor_${Date.now()}`,
      name: `Người dùng mới ${nextIdx}`,
      x: 115,
      y: 120 + (graph.actors.length) * 135,
    };
    const nextGraph = { ...graph, actors: [...graph.actors, newActor] };
    setGraph(nextGraph);
    setSelectedNode({ kind: 'actor', id: newActor.id });
    syncGraphToPlantUml(nextGraph);
  };

  // Thêm Chức năng (Use Case) mới trực tiếp trên Web
  const handleAddUseCase = () => {
    const nextIdx = graph.useCases.length + 1;
    const defaultActorId = graph.actors[0]?.id;
    const newUc = {
      id: `uc_${Date.now()}`,
      code: `UC-${String(nextIdx).padStart(2, '0')}`,
      name: `Chức năng mới ${nextIdx}`,
      x: nextIdx % 2 === 1 ? 460 : 730,
      y: 125 + Math.floor((nextIdx - 1) / 2) * 105,
    };
    const nextLinks = defaultActorId
      ? [
          ...graph.links,
          {
            id: `link_${Date.now()}`,
            from: defaultActorId,
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
    setSelectedNode({ kind: 'uc', id: newUc.id });
    syncGraphToPlantUml(nextGraph);
  };

  // Thêm đường nối mới giữa Actor -> Use Case hoặc giữa 2 Use Cases (<<include>> / <<extend>>)
  const handleAddLink = () => {
    if (!newLinkFrom || !newLinkTo || newLinkFrom === newLinkTo) return;
    const exists = graph.links.some(
      (l) => l.from === newLinkFrom && l.to === newLinkTo && l.type === newLinkType
    );
    if (exists) return;

    const nextGraph = {
      ...graph,
      links: [
        ...graph.links,
        {
          id: `link_${Date.now()}`,
          from: newLinkFrom,
          to: newLinkTo,
          type: newLinkType,
        },
      ],
    };
    setGraph(nextGraph);
    syncGraphToPlantUml(nextGraph);
  };

  // Đổi tên phần tử đang chọn
  const handleRenameSelected = (newName) => {
    if (!selectedNode) return;
    const nextGraph =
      selectedNode.kind === 'actor'
        ? {
            ...graph,
            actors: graph.actors.map((a) =>
              a.id === selectedNode.id ? { ...a, name: newName } : a
            ),
          }
        : {
            ...graph,
            useCases: graph.useCases.map((u) =>
              u.id === selectedNode.id ? { ...u, name: newName } : u
            ),
          };
    setGraph(nextGraph);
    syncGraphToPlantUml(nextGraph);
  };

  // Xóa phần tử đang chọn
  const handleDeleteSelected = () => {
    if (!selectedNode) return;
    const targetId = selectedNode.id;
    const nextGraph = {
      ...graph,
      actors: graph.actors.filter((a) => a.id !== targetId),
      useCases: graph.useCases.filter((u) => u.id !== targetId),
      links: graph.links.filter((l) => l.from !== targetId && l.to !== targetId),
    };
    setGraph(nextGraph);
    setSelectedNode(null);
    syncGraphToPlantUml(nextGraph);
  };

  // Sắp xếp lại bố cục chuẩn tự động
  const handleResetLayout = () => {
    const reset = buildInitialGraph(userStories, projectName);
    setGraph(reset);
    setSelectedNode(null);
    syncGraphToPlantUml(reset);
  };

  // Tải trực tiếp file ảnh Vector SVG từ bản vẽ trên Web
  const handleDownloadSvg = () => {
    const svgEl = svgRef.current;
    if (!svgEl) return;
    const serializer = new XMLSerializer();
    let source = serializer.serializeToString(svgEl);
    if (!source.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
      source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${projectName || 'UseCase'}_UML_Diagram.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Kết xuất trực tiếp bản vẽ SVG trên Web ra ảnh PNG độ phân giải cao (2x HD)
  const handleDownloadPngFromCanvas = () => {
    const svgEl = svgRef.current;
    if (!svgEl) return;
    const serializer = new XMLSerializer();
    let source = serializer.serializeToString(svgEl);
    if (!source.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
      source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    const svgBlob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);
    const img = new Image();
    img.onload = () => {
      const scale = 2; // 2x Retina HD
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
        a.download = `${projectName || 'UseCase'}_UML_Diagram.png`;
        a.click();
        URL.revokeObjectURL(pngUrl);
      }, 'image/png');
    };
    img.src = url;
  };

  // Lưu mã PlantUML khi sửa ở tab Code
  const handleApplyPlantUmlCode = async () => {
    setSyncMessage('Đang cập nhật mã PlantUML...');
    try {
      const resp = await fetch('/api/diagram/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plantuml_code: pumlText }),
      });
      if (resp.ok) {
        setSyncMessage('✓ Đã lưu và đồng bộ mã PlantUML thành công!');
      } else {
        setSyncMessage('Không thể cập nhật mã PlantUML.');
      }
    } catch {
      setSyncMessage('Lỗi kết nối khi lưu mã PlantUML.');
    }
  };

  // Tìm đối tượng đang được chọn để hiển thị trên thanh chỉnh sửa
  const selectedObj = useMemo(() => {
    if (!selectedNode) return null;
    if (selectedNode.kind === 'actor') {
      return graph.actors.find((a) => a.id === selectedNode.id) || null;
    }
    return graph.useCases.find((u) => u.id === selectedNode.id) || null;
  }, [selectedNode, graph]);

  // Danh sách tất cả các nút để chọn nối dây
  const allNodesForLink = useMemo(() => {
    return [
      ...graph.actors.map((a) => ({ id: a.id, label: `[Người dùng] ${a.name}` })),
      ...graph.useCases.map((u) => ({ id: u.id, label: `[Chức năng] ${u.code}: ${u.name}` })),
    ];
  }, [graph]);

  // Bảng tra cứu tọa độ của từng nút để vẽ đường nối SVG
  const nodeCoordsMap = useMemo(() => {
    const map = {};
    graph.actors.forEach((a) => {
      map[a.id] = { x: a.x, y: a.y, kind: 'actor' };
    });
    graph.useCases.forEach((u) => {
      map[u.id] = { x: u.x, y: u.y, kind: 'uc' };
    });
    return map;
  }, [graph]);

  return (
    <div className="card" style={{ marginBottom: '22px' }}>
      {/* TOP BAR: SWITCH BETWEEN VISUAL CANVAS & PLANTUML CODE */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
          paddingBottom: '14px',
          marginBottom: '16px',
          borderBottom: '1px solid #E2E8F0',
        }}
      >
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A' }}>
            Bảng Vẽ Sơ đồ UML Trực tiếp trên Web (Kéo - Thả &amp; Chỉnh sửa Tương tác)
          </h3>
          <p style={{ fontSize: '0.84rem', color: '#64748B' }}>
            Dùng chuột kéo-thả vị trí các hình trên bản vẽ, bấm vào hình bất kỳ để đổi tên hoặc thêm mới Người dùng &amp; Chức năng
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            type="button"
            className={`filter-tab ${mode === 'canvas' ? 'active' : ''}`}
            onClick={() => setMode('canvas')}
          >
            Bảng vẽ Kéo - Thả trực quan
          </button>
          <button
            type="button"
            className={`filter-tab ${mode === 'code' ? 'active' : ''}`}
            onClick={() => setMode('code')}
          >
            Mã nguồn PlantUML (@startuml)
          </button>
        </div>
      </div>

      {mode === 'canvas' && (
        <div>
          {/* VISUAL DRAWING TOOLBAR */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '10px',
              flexWrap: 'wrap',
              background: '#F8FAFC',
              border: '1px solid #E2E8F0',
              borderRadius: '10px',
              padding: '10px 14px',
              marginBottom: '14px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-primary"
                style={{ padding: '7px 13px', fontSize: '0.84rem' }}
                onClick={handleAddActor}
              >
                + Thêm Người dùng (Actor)
              </button>
              <button
                type="button"
                className="btn btn-primary"
                style={{ padding: '7px 13px', fontSize: '0.84rem', background: '#0F766E' }}
                onClick={handleAddUseCase}
              >
                + Thêm Chức năng (Use Case)
              </button>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '7px 12px', fontSize: '0.82rem' }}
                onClick={handleResetLayout}
              >
                Sắp xếp lại tự động
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '6px 10px', fontSize: '0.8rem' }}
                onClick={() => setZoom((z) => Math.max(0.7, Number((z - 0.1).toFixed(1))))}
              >
                Thu nhỏ (-)
              </button>
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#475569' }}>
                {Math.round(zoom * 100)}%
              </span>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '6px 10px', fontSize: '0.8rem' }}
                onClick={() => setZoom((z) => Math.min(1.4, Number((z + 0.1).toFixed(1))))}
              >
                Phóng to (+)
              </button>
              <button
                type="button"
                className="btn btn-success"
                style={{ padding: '7px 14px', fontSize: '0.84rem' }}
                onClick={handleDownloadPngFromCanvas}
              >
                Tải Ảnh Sơ đồ (.png)
              </button>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '7px 12px', fontSize: '0.82rem' }}
                onClick={handleDownloadSvg}
              >
                Tải Vector (.svg)
              </button>
            </div>
          </div>

          {/* QUICK CONNECTOR / LINK BUILDER BAR */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flexWrap: 'wrap',
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '10px',
              padding: '9px 14px',
              marginBottom: '14px',
              fontSize: '0.84rem',
            }}
          >
            <strong style={{ color: '#334155' }}>Nối dây quan hệ:</strong>
            <select
              className="select-field"
              style={{ width: 'auto', maxWidth: '220px', padding: '6px 10px', fontSize: '0.82rem' }}
              value={newLinkFrom}
              onChange={(e) => setNewLinkFrom(e.target.value)}
            >
              <option value="">-- Chọn điểm đầu --</option>
              {allNodesForLink.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.label}
                </option>
              ))}
            </select>

            <select
              className="select-field"
              style={{ width: 'auto', padding: '6px 10px', fontSize: '0.82rem' }}
              value={newLinkType}
              onChange={(e) => setNewLinkType(e.target.value)}
            >
              <option value="association">⎯⎯▶ Sử dụng trực tiếp</option>
              <option value="include">- - ▶ &lt;&lt;include&gt;&gt; (Bắt buộc kèm)</option>
              <option value="extend">- - ▶ &lt;&lt;extend&gt;&gt; (Mở rộng thêm)</option>
            </select>

            <select
              className="select-field"
              style={{ width: 'auto', maxWidth: '220px', padding: '6px 10px', fontSize: '0.82rem' }}
              value={newLinkTo}
              onChange={(e) => setNewLinkTo(e.target.value)}
            >
              <option value="">-- Chọn chức năng đích --</option>
              {graph.useCases.map((u) => (
                <option key={u.id} value={u.id}>
                  [Chức năng] {u.code}: {u.name}
                </option>
              ))}
            </select>

            <button
              type="button"
              className="btn btn-outline"
              style={{ padding: '6px 12px', fontSize: '0.82rem' }}
              onClick={handleAddLink}
            >
              + Tạo đường nối
            </button>
          </div>

          {/* SELECTED ELEMENT INSPECTOR BAR (WHEN USER CLICKS ANY NODE ON CANVAS) */}
          {selectedObj && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
                flexWrap: 'wrap',
                background: '#EFF6FF',
                border: '1px solid #93C5FD',
                borderRadius: '10px',
                padding: '10px 14px',
                marginBottom: '14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '260px' }}>
                <span className="badge badge-num">
                  {selectedNode.kind === 'actor' ? 'Đang chọn Người dùng' : `Đang chọn ${selectedObj.code}`}
                </span>
                <input
                  type="text"
                  className="input-field"
                  style={{ padding: '6px 12px', fontSize: '0.9rem', maxWidth: '420px' }}
                  value={selectedObj.name}
                  onChange={(e) => handleRenameSelected(e.target.value)}
                />
              </div>

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
                  Xóa khỏi sơ đồ
                </button>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ padding: '6px 12px', fontSize: '0.82rem' }}
                  onClick={() => setSelectedNode(null)}
                >
                  Xong
                </button>
              </div>
            </div>
          )}

          {/* INTERACTIVE SVG UML 2.5 CANVAS */}
          <div
            style={{
              background: '#FFFFFF',
              border: '2px solid #CBD5E1',
              borderRadius: '12px',
              overflow: 'auto',
              maxHeight: '640px',
              position: 'relative',
              boxShadow: 'inset 0 2px 6px rgba(15, 23, 42, 0.04)',
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
                userSelect: 'none',
                cursor: dragging ? 'grabbing' : 'default',
                background: '#FFFFFF',
              }}
              onPointerMove={handlePointerMoveCanvas}
              onPointerUp={handlePointerUpCanvas}
              onPointerLeave={handlePointerUpCanvas}
              onClick={() => setSelectedNode(null)}
            >
              <defs>
                {/* Mũi tên chuẩn UML */}
                <marker
                  id="uml-arrow"
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#334155" />
                </marker>
                <marker
                  id="uml-arrow-dashed"
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 1 1 L 9 5 L 1 9" fill="none" stroke="#1D4ED8" strokeWidth="1.8" />
                </marker>
                <pattern id="uml-grid" width="24" height="24" patternUnits="userSpaceOnUse">
                  <circle cx="2" cy="2" r="1" fill="#E2E8F0" />
                </pattern>
              </defs>

              {/* Nền lưới chấm kỹ thuật */}
              <rect x="0" y="0" width={canvasWidth} height={canvasHeight} fill="url(#uml-grid)" />

              {/* KHUNG RANH GIỚI HỆ THỐNG (SYSTEM BOUNDARY BOX) */}
              <rect
                x="280"
                y="32"
                width="640"
                height={canvasHeight - 64}
                rx="12"
                fill="#F8FAFC"
                stroke="#334155"
                strokeWidth="2"
              />
              <rect
                x="280"
                y="32"
                width="640"
                height="40"
                rx="12"
                fill="#0F172A"
              />
              <text
                x="600"
                y="57"
                textAnchor="middle"
                fill="#FFFFFF"
                fontFamily="Be Vietnam Pro, sans-serif"
                fontSize="14.5"
                fontWeight="700"
              >
                Hệ thống: {graph.systemTitle}
              </text>

              {/* ĐƯỜNG NỐI QUAN HỆ (ASSOCIATIONS & INCLUDE / EXTEND) */}
              {graph.links.map((lnk) => {
                const src = nodeCoordsMap[lnk.from];
                const dst = nodeCoordsMap[lnk.to];
                if (!src || !dst) return null;

                const x1 = src.kind === 'actor' ? src.x + 32 : src.x;
                const y1 = src.y;
                const x2 = dst.kind === 'uc' && src.kind === 'actor' ? dst.x - 118 : dst.x;
                const y2 = dst.y;
                const midX = (x1 + x2) / 2;
                const midY = (y1 + y2) / 2;
                const isSpecial = lnk.type === 'include' || lnk.type === 'extend';

                return (
                  <g key={lnk.id}>
                    <path
                      d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                      fill="none"
                      stroke={isSpecial ? '#1D4ED8' : '#475569'}
                      strokeWidth={isSpecial ? '1.8' : '1.7'}
                      strokeDasharray={isSpecial ? '6 4' : 'none'}
                      markerEnd={isSpecial ? 'url(#uml-arrow-dashed)' : 'url(#uml-arrow)'}
                    />
                    {isSpecial && (
                      <text
                        x={midX}
                        y={midY - 6}
                        textAnchor="middle"
                        fill="#1D4ED8"
                        fontFamily="JetBrains Mono, monospace"
                        fontSize="11"
                        fontWeight="600"
                      >
                        {`<<${lnk.type}>>`}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* VẼ CÁC TÁC NHÂN (UML STICK-MAN ACTORS) */}
              {graph.actors.map((actor) => {
                const isSel = selectedNode?.kind === 'actor' && selectedNode?.id === actor.id;
                return (
                  <g
                    key={actor.id}
                    transform={`translate(${actor.x}, ${actor.y})`}
                    style={{ cursor: 'grab' }}
                    onPointerDown={(e) => handlePointerDownNode(e, 'actor', actor)}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {isSel && (
                      <rect
                        x="-58"
                        y="-45"
                        width="116"
                        height="108"
                        rx="10"
                        fill="rgba(37, 99, 235, 0.08)"
                        stroke="#2563EB"
                        strokeWidth="2"
                        strokeDasharray="4 3"
                      />
                    )}
                    {/* Đầu Actor */}
                    <circle
                      cx="0"
                      cy="-22"
                      r="12"
                      fill="#F0FDFA"
                      stroke="#0F766E"
                      strokeWidth="2.5"
                    />
                    {/* Thân & Tay Chân Actor chuẩn UML */}
                    <line x1="0" y1="-10" x2="0" y2="16" stroke="#0F766E" strokeWidth="2.5" />
                    <line x1="-18" y1="-1" x2="18" y2="-1" stroke="#0F766E" strokeWidth="2.5" />
                    <line x1="0" y1="16" x2="-15" y2="36" stroke="#0F766E" strokeWidth="2.5" />
                    <line x1="0" y1="16" x2="15" y2="36" stroke="#0F766E" strokeWidth="2.5" />

                    {/* Nhãn tên Actor */}
                    <rect
                      x="-62"
                      y="41"
                      width="124"
                      height="22"
                      rx="6"
                      fill="#0F172A"
                    />
                    <text
                      x="0"
                      y="56"
                      textAnchor="middle"
                      fill="#FFFFFF"
                      fontFamily="Be Vietnam Pro, sans-serif"
                      fontSize="11.5"
                      fontWeight="600"
                    >
                      {actor.name.length > 18 ? actor.name.slice(0, 17) + '…' : actor.name}
                    </text>
                  </g>
                );
              })}

              {/* VẼ CÁC CHỨC NĂNG (UML USE CASE ELLIPSES) */}
              {graph.useCases.map((uc) => {
                const isSel = selectedNode?.kind === 'uc' && selectedNode?.id === uc.id;
                const lines = wrapLabel(uc.name, 25);
                return (
                  <g
                    key={uc.id}
                    transform={`translate(${uc.x}, ${uc.y})`}
                    style={{ cursor: 'grab' }}
                    onPointerDown={(e) => handlePointerDownNode(e, 'uc', uc)}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ellipse
                      cx="0"
                      cy="0"
                      rx="118"
                      ry="36"
                      fill={isSel ? '#DBEAFE' : '#EFF6FF'}
                      stroke={isSel ? '#1D4ED8' : '#2563EB'}
                      strokeWidth={isSel ? '2.8' : '2'}
                    />
                    {/* Mã UC nhỏ phía trên */}
                    <text
                      x="0"
                      y={lines.length > 1 ? -14 : -8}
                      textAnchor="middle"
                      fill="#1D4ED8"
                      fontFamily="JetBrains Mono, monospace"
                      fontSize="10.5"
                      fontWeight="700"
                    >
                      {uc.code}
                    </text>
                    {/* Tên chức năng chia dòng tự động */}
                    {lines.map((ln, lIdx) => (
                      <text
                        key={lIdx}
                        x="0"
                        y={(lines.length > 1 ? 2 : 8) + lIdx * 14}
                        textAnchor="middle"
                        fill="#0F172A"
                        fontFamily="Be Vietnam Pro, sans-serif"
                        fontSize="12"
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

      {/* CHẾ ĐỘ 2: SOẠN THẢO MÃ PLANTUML TRỰC TIẾP */}
      {mode === 'code' && (
        <div>
          <div style={{ marginBottom: '12px', fontSize: '0.88rem', color: '#475569' }}>
            Mã PlantUML dưới đây được đồng bộ tự động từ Bảng vẽ Kéo - Thả. Bạn cũng có thể sửa mã trực tiếp và lưu lại:
          </div>
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
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ fontSize: '0.86rem', color: '#15803D', fontWeight: 600 }}>
              {syncMessage}
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <a
                href="/api/export/diagram-puml"
                download={`${projectName}_usecase.puml`}
                className="btn btn-outline"
              >
                Tải File PlantUML (.puml)
              </a>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleApplyPlantUmlCode}
              >
                Lưu &amp; Kết xuất lại Sơ đồ
              </button>
            </div>
          </div>

          {hasKrokiImage && (
            <div
              style={{
                marginTop: '18px',
                padding: '16px',
                background: '#F8FAFC',
                border: '1px solid #E2E8F0',
                borderRadius: '10px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#475569', marginBottom: '10px' }}>
                Ảnh kết xuất từ máy chủ PlantUML (Kroki):
              </div>
              <img
                src={`/api/export/diagram-png?t=${Date.now()}`}
                alt="PlantUML Rendered Diagram"
                style={{ maxWidth: '100%', height: 'auto', borderRadius: '6px' }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

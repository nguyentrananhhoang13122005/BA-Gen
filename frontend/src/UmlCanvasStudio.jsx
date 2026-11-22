import React, { useEffect, useMemo, useRef, useState } from 'react';

function wrapUseCaseText(text, maxChars = 22) {
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

function getEllipseRadii(name) {
  const lines = wrapUseCaseText(name, 22);
  const longest = Math.max(...lines.map((l) => l.length), 10);
  const rx = Math.max(95, Math.min(128, Math.round(longest * 3.8 + 26)));
  const ry = lines.length >= 3 ? 38 : lines.length === 2 ? 33 : 28;
  return { rx, ry, lines };
}

function computePerimeterPoints(srcNode, dstNode) {
  const dx = dstNode.x - srcNode.x;
  const dy = dstNode.y - srcNode.y;
  const angle = Math.atan2(dy, dx);

  let x1 = srcNode.x;
  let y1 = srcNode.y;
  if (srcNode.kind === 'actor') {
    x1 = srcNode.x + Math.cos(angle) * 30;
    y1 = srcNode.y + Math.sin(angle) * 34;
  } else {
    const { rx, ry } = getEllipseRadii(srcNode.name);
    x1 = srcNode.x + (rx + 2) * Math.cos(angle);
    y1 = srcNode.y + (ry + 2) * Math.sin(angle);
  }

  const backAngle = angle + Math.PI;
  let x2 = dstNode.x;
  let y2 = dstNode.y;
  if (dstNode.kind === 'actor') {
    x2 = dstNode.x + Math.cos(backAngle) * 30;
    y2 = dstNode.y + Math.sin(backAngle) * 34;
  } else {
    const { rx, ry } = getEllipseRadii(dstNode.name);
    x2 = dstNode.x + (rx + 3) * Math.cos(backAngle);
    y2 = dstNode.y + (ry + 3) * Math.sin(backAngle);
  }

  return { x1, y1, x2, y2 };
}

function cleanSystemTitle(rawTitle) {
  if (!rawTitle) return 'Hệ thống Phần mềm';
  let cleaned = rawTitle
    .replace(/\.(docx|txt|md|pdf)$/i, '')
    .replace(/^Topic\s+\d+\s*[—\-:]\s*/i, '')
    .replace(/_/g, ' ')
    .trim();

  // Loại bỏ tiền tố tên file/tài liệu như "Tài liệu BA", "Tai lieu BA", "BRD", "SRS"
  cleaned = cleaned
    .replace(/^(Tài\s+liệu\s+BA|Tai\s+lieu\s+BA|Tài\s+liệu\s+SRS|BRD|SRS)\s*[—\-:]?\s*/i, '')
    .trim();

  if (/^Quan\s+ly\s+Nhan\s+vien$/i.test(cleaned)) {
    return 'Hệ thống Quản lý Nhân sự (HRM)';
  }
  if (cleaned && !/^(Hệ\s+thống|System|Phần\s+mềm)\b/i.test(cleaned)) {
    if (/^(Quản\s+lý|Quan\s+ly)\b/i.test(cleaned)) {
      cleaned = `Hệ thống ${cleaned}`;
    }
  }
  return cleaned || 'Hệ thống Phần mềm';
}

function stripUseCasePrefixAndActor(rawName) {
  let cleaned = (rawName || '').trim();
  // Loại bỏ tiền tố FR-01:, UC-01:, REQ-01:, BR-01:
  cleaned = cleaned.replace(/^(?:FR|UC|REQ|NFR|BR|US)\s*[-_]?\s*\d+\s*[—\-:.)]*\s*/i, '').trim();
  // Loại bỏ tên Actor ở đầu tên Use Case
  cleaned = cleaned
    .replace(
      /^(?:Quản\s+trị\s+viên(?:\s+hệ\s+thống)?|Chuyên\s+viên\s+Nhân\s+sự(?:\s*\(HR\))?|Quản\s+lý\s+trực\s+tiếp|Nhân\s+viên|Kế\s+toán|Thủ\s+kho|Khách\s+hàng|HR)\s*[—\-:]\s*/i,
      ''
    )
    .trim();
  if (!cleaned) return (rawName || '').trim();
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function isSecondaryActorRole(roleName) {
  const low = (roleName || '').toLowerCase();
  return (
    low.includes('quản trị') ||
    low.includes('admin') ||
    low.includes('quản lý trực tiếp') ||
    low.includes('line manager') ||
    low.includes('phê duyệt') ||
    low.includes('hệ thống') ||
    low.includes('tích hợp') ||
    low.includes('kế toán')
  );
}

/**
 * Lọc danh sách User Stories chức năng (FR), loại bỏ NFR và các câu tiêu đề trùng lặp
 */
function filterFunctionalStories(userStories = [], requirements = [], actorFilter = 'core') {
  const reqTypeMap = {};
  requirements.forEach((r) => {
    reqTypeMap[r.req_id] = r.req_type;
  });

  // 1. Chỉ giữ các câu Chức năng (FR) trên sơ đồ Use Case UML
  let frStories = userStories.filter((us) => {
    const rType = reqTypeMap[us.req_id];
    if (rType && rType !== 'FR') return false;
    const name = (us.puml_usecase_name || '').trim();
    if (!name || name.length < 4) return false;
    // Loại bỏ các nhãn là tiêu đề chương hoặc quy tắc BR-xx
    if (/^(TỔNG QUAN|ĐỐI TƯỢNG|ĐẶC TẢ|QUY TẮC|YÊU CẦU|TÀI LIỆU|Mục tiêu chính|Phạm vi hệ thống|BR-\d+)/i.test(name)) {
      return false;
    }
    return true;
  });

  if (frStories.length === 0) {
    frStories = userStories;
  }

  // 2. Khử trùng lặp tên Use Case (sau khi đã chuẩn hóa bỏ mã FR-xx/UC-xx)
  const seenNames = new Set();
  const deduped = [];
  frStories.forEach((us) => {
    const cleanName = stripUseCasePrefixAndActor(us.puml_usecase_name || us.goal || '');
    const key = cleanName.toLowerCase();
    if (!seenNames.has(key)) {
      seenNames.add(key);
      deduped.push({
        ...us,
        puml_usecase_name: cleanName,
      });
    }
  });

  // 3. Lọc theo chế độ xem (Core <= 10 chức năng chính, hoặc theo từng Actor cụ thể)
  if (actorFilter === 'core') {
    // Ưu tiên các câu có mã FR-xx hoặc lấy tối đa 10 chức năng chính phân bổ đều các Actor
    return deduped.slice(0, 10);
  }
  if (actorFilter !== 'all') {
    return deduped.filter((us) => (us.role || '').trim() === actorFilter);
  }
  return deduped;
}

/**
 * Xây dựng bố cục UML 2.5 Hai Bên (Dual-Side StarUML Layout):
 * - Primary Actors ở bên Trái nối vào cột Use Case bên Trái
 * - Secondary Actors / Quản trị / Phê duyệt ở bên Phải nối vào cột Use Case bên Phải
 * - Hỗ trợ phân tách Use Case con (<<include>> / <<extend>>) ở cột giữa mà KHÔNG nối trực tiếp với Actor
 * -> KHÔNG BAO GIỜ CÓ ĐƯỜNG NỐI CẮT ĐÈ LÊN HÌNH ELIP!
 */
function buildDualSideGraph(
  filteredStories = [],
  projectName = 'Hệ thống Phần mềm',
  showSubUseCases = false
) {
  const actorNames = Array.from(
    new Set(filteredStories.map((u) => (u.role || 'Người dùng').trim()))
  );

  // Phân loại Primary Actors (bên Trái) và Secondary Actors (bên Phải)
  const leftActorSet = new Set();
  const rightActorSet = new Set();

  if (actorNames.length === 1) {
    leftActorSet.add(actorNames[0]);
  } else {
    actorNames.forEach((name) => {
      if (isSecondaryActorRole(name)) {
        rightActorSet.add(name);
      } else {
        leftActorSet.add(name);
      }
    });
    // Nếu tất cả rơi vào 1 bên, chia đều 2 bên để không bị chồng đường nối
    if (leftActorSet.size === 0 || rightActorSet.size === 0) {
      leftActorSet.clear();
      rightActorSet.clear();
      actorNames.forEach((name, idx) => {
        if (idx % 2 === 0) leftActorSet.add(name);
        else rightActorSet.add(name);
      });
    }
  }

  const actorMap = new Map();
  actorNames.forEach((name, idx) => {
    const isLeft = leftActorSet.has(name);
    actorMap.set(name, {
      id: `actor_${idx + 1}`,
      name,
      side: isLeft ? 'left' : 'right',
      x: isLeft ? 92 : 1168,
      y: 160,
    });
  });

  const useCases = [];
  const links = [];
  const leftUcs = [];
  const rightUcs = [];
  const centerSubUcs = [];

  filteredStories.forEach((us, idx) => {
    const roleName = (us.role || 'Người dùng').trim();
    const actor = actorMap.get(roleName);
    const ucId = `uc_${idx + 1}`;
    const ucName = stripUseCasePrefixAndActor(
      us.puml_usecase_name || us.goal || `Chức năng ${idx + 1}`
    );

    const ucNode = {
      id: ucId,
      code: `UC-${String(idx + 1).padStart(2, '0')}`,
      name: ucName,
      actorName: roleName,
      side: actor?.side || 'left',
      isSubUseCase: false,
      subUseCases: Array.isArray(us.sub_usecases) ? us.sub_usecases : [],
      x: 0,
      y: 0,
    };

    useCases.push(ucNode);
    if (ucNode.side === 'left') leftUcs.push(ucNode);
    else rightUcs.push(ucNode);

    if (actor) {
      links.push({
        id: `link_assoc_${idx + 1}`,
        from: actor.id,
        to: ucId,
        type: 'association',
      });
    }
  });

  // Sắp xếp Use Case ở mỗi cột gom theo thứ tự từng Actor để các đường nối của 2 Actor cùng bên KHÔNG BAO GIỜ cắt chéo nhau!
  const leftActorOrder = Array.from(leftActorSet);
  const rightActorOrder = Array.from(rightActorSet);

  leftUcs.sort(
    (a, b) => leftActorOrder.indexOf(a.actorName) - leftActorOrder.indexOf(b.actorName)
  );
  rightUcs.sort(
    (a, b) => rightActorOrder.indexOf(a.actorName) - rightActorOrder.indexOf(b.actorName)
  );

  const singleSideMode = rightUcs.length === 0;

  if (singleSideMode) {
    leftUcs.forEach((uc, i) => {
      uc.x = showSubUseCases ? 430 : 630;
      uc.y = 115 + i * 96;
    });
  } else {
    // Cột Trái nối thẳng với Primary Actor Trái (tâm x=345 khi bật sub-UC, cách cột giữa 285px nên không bao giờ chạm hình elip)
    leftUcs.forEach((uc, i) => {
      uc.x = showSubUseCases ? 345 : 435;
      uc.y = 115 + i * 98;
    });
    // Cột Phải nối thẳng với Secondary Actor Phải (tâm x=915 khi bật sub-UC, cách cột giữa 285px)
    rightUcs.forEach((uc, i) => {
      uc.x = showSubUseCases ? 915 : 825;
      uc.y = 115 + i * 98;
    });
  }

  // Nếu bật chế độ hiển thị Use Case con (<<include>> / <<extend>>)
  if (showSubUseCases) {
    let subCounter = 0;
    const allMainUcs = [...leftUcs, ...rightUcs];
    allMainUcs.forEach((parentUc) => {
      const subs = (parentUc.subUseCases || []).slice(0, 1);
      subs.forEach((subItem) => {
        const subName = stripUseCasePrefixAndActor(subItem.target_name || '');
        if (!subName || subName.toLowerCase() === parentUc.name.toLowerCase()) return;
        subCounter += 1;
        const subId = `sub_uc_${subCounter}`;
        const relType = subItem.rel_type === 'extend' ? 'extend' : 'include';
        const subNode = {
          id: subId,
          code: `SUB-${String(subCounter).padStart(2, '0')}`,
          name: subName,
          actorName: parentUc.actorName,
          side: 'center',
          isSubUseCase: true,
          x: singleSideMode ? 825 : 630,
          y: parentUc.y,
        };
        centerSubUcs.push(subNode);
        useCases.push(subNode);
        // Quy tắc UML 2.5: chỉ nối từ Use Case cha sang Use Case con (<<include>>/<<extend>>), KHÔNG nối từ Actor vào Use Case con
        links.push({
          id: `link_sub_${subCounter}`,
          from: parentUc.id,
          to: subId,
          type: relType,
        });
      });
    });

    // Chống trùng tọa độ Y ở cột giữa cho các Use Case con
    centerSubUcs.sort((a, b) => a.y - b.y);
    for (let i = 1; i < centerSubUcs.length; i++) {
      if (centerSubUcs[i].y - centerSubUcs[i - 1].y < 86) {
        centerSubUcs[i].y = centerSubUcs[i - 1].y + 86;
      }
    }
  }

  const maxSubY = centerSubUcs.length ? Math.max(...centerSubUcs.map((u) => u.y)) : 0;
  const maxMainRows = Math.max(leftUcs.length, rightUcs.length, 1);
  const totalH = Math.max(115 + maxMainRows * 98 + 65, maxSubY + 95, 440);

  // Đặt tọa độ Y của từng Actor đúng bằng trung bình cộng Y của nhóm Use Case thuộc Actor đó!
  const actors = Array.from(actorMap.values());
  const placeActorsAlignedWithUcs = (sideActors, sideUcs) => {
    if (sideActors.length === 0) return;
    sideActors.forEach((actor) => {
      const myUcs = sideUcs.filter((u) => u.actorName === actor.name);
      if (myUcs.length > 0) {
        const avgY = myUcs.reduce((sum, u) => sum + u.y, 0) / myUcs.length;
        actor.y = Math.round(avgY);
      } else {
        actor.y = Math.round(totalH / 2);
      }
    });
    // Đảm bảo khoảng cách tối thiểu 125px giữa 2 Actor cùng bên để nhãn tên không đè lên nhau
    for (let i = 1; i < sideActors.length; i++) {
      if (sideActors[i].y - sideActors[i - 1].y < 125) {
        sideActors[i].y = sideActors[i - 1].y + 125;
      }
    }
  };

  placeActorsAlignedWithUcs(
    actors.filter((a) => a.side === 'left'),
    leftUcs
  );
  placeActorsAlignedWithUcs(
    actors.filter((a) => a.side === 'right'),
    rightUcs
  );

  return {
    systemTitle: cleanSystemTitle(projectName),
    actors,
    useCases,
    links,
  };
}

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
  requirements = [],
  projectName = 'Hệ thống Phần mềm',
  initialPlantUmlCode = '',
}) {
  // Chế độ lọc chống rối mắt: 'core' (<= 10 chức năng cốt lõi) | tên Actor | 'all'
  const [actorFilter, setActorFilter] = useState('core');
  // Mặc định bật phân tách Use Case con (<<include>> / <<extend>>) khi xem theo 1 Actor, hoặc bật thủ công
  const [showSubUseCases, setShowSubUseCases] = useState(false);

  const allFunctionalStories = useMemo(
    () => filterFunctionalStories(userStories, requirements, 'all'),
    [userStories, requirements]
  );

  const uniqueActors = useMemo(
    () => Array.from(new Set(allFunctionalStories.map((u) => (u.role || 'Người dùng').trim()))),
    [allFunctionalStories]
  );

  const visibleStories = useMemo(
    () => filterFunctionalStories(userStories, requirements, actorFilter),
    [userStories, requirements, actorFilter]
  );

  const [graph, setGraph] = useState(() =>
    buildDualSideGraph(visibleStories, projectName, showSubUseCases)
  );
  const [selectedItem, setSelectedItem] = useState(null);
  const [dragging, setDragging] = useState(null);
  const [connectMode, setConnectMode] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [tableZoom, setTableZoom] = useState(1);
  const [showAdvancedTools, setShowAdvancedTools] = useState(false);
  const [mode, setMode] = useState('canvas');
  const [pumlText, setPumlText] = useState(initialPlantUmlCode);
  const [syncMessage, setSyncMessage] = useState('');

  const svgRef = useRef(null);

  useEffect(() => {
    const nextGraph = buildDualSideGraph(visibleStories, projectName, showSubUseCases);
    setGraph(nextGraph);
    setPumlText(generatePlantUmlFromGraph(nextGraph));
    setSelectedItem(null);
    setConnectMode(null);
  }, [visibleStories, projectName, showSubUseCases]);

  const syncToBackend = (updatedGraph) => {
    const code = generatePlantUmlFromGraph(updatedGraph);
    setPumlText(code);
    fetch('/api/diagram/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plantuml_code: code }),
    }).catch(() => {});
  };

  const canvasWidth = 1260;
  const canvasHeight = useMemo(() => {
    const maxA = graph.actors.length ? Math.max(...graph.actors.map((a) => a.y)) : 280;
    const maxU = graph.useCases.length ? Math.max(...graph.useCases.map((u) => u.y)) : 280;
    return Math.max(maxA + 110, maxU + 95, 440);
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

  const handlePointerDownNode = (e, kind, item) => {
    e.stopPropagation();

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
    const snappedX = Math.round((pt.x - dragging.offsetX) / 8) * 8;
    const snappedY = Math.round((pt.y - dragging.offsetY) / 8) * 8;
    const nextX = Math.max(65, Math.min(canvasWidth - 65, snappedX));
    const nextY = Math.max(85, Math.min(canvasHeight - 60, snappedY));

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
    const isLeft = idx % 2 === 1;
    const newActor = {
      id: `actor_${Date.now()}`,
      name: `Actor mới ${idx}`,
      side: isLeft ? 'left' : 'right',
      x: isLeft ? 92 : 1168,
      y: Math.round(canvasHeight / 2),
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
      name: `Chức năng mới ${idx}`,
      side: 'left',
      x: 630,
      y: Math.min(canvasHeight - 80, 120 + (idx - 1) * 85),
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
    const fresh = buildDualSideGraph(visibleStories, projectName, showSubUseCases);
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
      {/* HEADER BAR - GỌN GÀNG, DỄ HIỂU */}
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
            Sơ đồ Chức năng Hệ thống (Ai làm được việc gì?)
          </h3>
          <p style={{ fontSize: '0.84rem', color: '#64748B' }}>
            Bấm chọn từng nhóm người dùng để xem riêng chức năng của họ, hoặc dùng nút <strong>− / +</strong> để thu nhỏ, phóng to toàn bộ sơ đồ
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* CỤM NÚT ZOOM IN / ZOOM OUT NỔI BẬT NGAY TRÊN ĐẦU */}
          {mode === 'canvas' ? (
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: '#EFF6FF',
                border: '1.5px solid #93C5FD',
                borderRadius: '8px',
                padding: '4px 8px',
              }}
            >
              <button
                type="button"
                className="btn btn-outline"
                title="Thu nhỏ sơ đồ"
                style={{
                  padding: '4px 10px',
                  fontSize: '0.95rem',
                  fontWeight: 800,
                  background: '#FFFFFF',
                  minWidth: '34px',
                }}
                onClick={() => setZoom((z) => Math.max(0.5, Number((z - 0.15).toFixed(2))))}
              >
                −
              </button>
              <button
                type="button"
                className="btn btn-outline"
                title="Bấm để đưa về kích thước vừa khít màn hình (100%)"
                style={{
                  padding: '4px 10px',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  background: zoom === 1 ? '#2563EB' : '#FFFFFF',
                  color: zoom === 1 ? '#FFFFFF' : '#1E3A8A',
                  borderColor: zoom === 1 ? '#2563EB' : '#CBD5E1',
                }}
                onClick={() => setZoom(1)}
              >
                {Math.round(zoom * 100)}% (Vừa khung)
              </button>
              <button
                type="button"
                className="btn btn-outline"
                title="Phóng to sơ đồ"
                style={{
                  padding: '4px 10px',
                  fontSize: '0.95rem',
                  fontWeight: 800,
                  background: '#FFFFFF',
                  minWidth: '34px',
                }}
                onClick={() => setZoom((z) => Math.min(2.0, Number((z + 0.15).toFixed(2))))}
              >
                +
              </button>
            </div>
          ) : (
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: '#EFF6FF',
                border: '1.5px solid #93C5FD',
                borderRadius: '8px',
                padding: '4px 8px',
              }}
            >
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '0.95rem', fontWeight: 800, background: '#FFFFFF' }}
                onClick={() => setTableZoom((z) => Math.max(0.75, Number((z - 0.1).toFixed(2))))}
              >
                −
              </button>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '0.8rem', fontWeight: 700, background: '#FFFFFF' }}
                onClick={() => setTableZoom(1)}
              >
                Cỡ bảng: {Math.round(tableZoom * 100)}%
              </button>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '0.95rem', fontWeight: 800, background: '#FFFFFF' }}
                onClick={() => setTableZoom((z) => Math.min(1.4, Number((z + 0.1).toFixed(2))))}
              >
                +
              </button>
            </div>
          )}

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
            className={`btn ${showAdvancedTools ? 'btn-primary' : 'btn-outline'}`}
            style={{
              padding: '7px 12px',
              fontSize: '0.82rem',
              background: showAdvancedTools ? '#1E3A8A' : '#FFFFFF',
              color: showAdvancedTools ? '#FFFFFF' : '#334155',
            }}
            onClick={() => setShowAdvancedTools((prev) => !prev)}
          >
            {showAdvancedTools ? '▲ Ẩn công cụ chỉnh sửa' : '⚙️ Tùy chọn & Chỉnh sửa sơ đồ'}
          </button>
        </div>
      </div>

      {/* THANH LỌC THEO NGƯỜI DÙNG (ĐƠN GIẢN, DỄ HIỂU) */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
          marginBottom: '12px',
          padding: '10px 14px',
          background: '#F8FAFC',
          border: '1px solid #E2E8F0',
          borderRadius: '10px',
        }}
      >
        <span style={{ fontSize: '0.83rem', fontWeight: 700, color: '#334155' }}>
          Xem theo người dùng:
        </span>
        <button
          type="button"
          className={`filter-tab ${actorFilter === 'core' ? 'active' : ''}`}
          style={{ padding: '5px 12px', fontSize: '0.8rem' }}
          onClick={() => setActorFilter('core')}
        >
          ★ Tóm tắt ({Math.min(allFunctionalStories.length, 10)} chức năng chính)
        </button>

        {uniqueActors.map((actName) => {
          const cnt = allFunctionalStories.filter(
            (u) => (u.role || 'Người dùng').trim() === actName
          ).length;
          return (
            <button
              key={actName}
              type="button"
              className={`filter-tab ${actorFilter === actName ? 'active' : ''}`}
              style={{ padding: '5px 12px', fontSize: '0.8rem' }}
              onClick={() => setActorFilter(actName)}
            >
              👤 {actName} ({cnt})
            </button>
          );
        })}

        {allFunctionalStories.length > 10 && (
          <button
            type="button"
            className={`filter-tab ${actorFilter === 'all' ? 'active' : ''}`}
            style={{ padding: '5px 12px', fontSize: '0.8rem' }}
            onClick={() => setActorFilter('all')}
          >
            Xem tất cả ({allFunctionalStories.length})
          </button>
        )}

        <button
          type="button"
          className={`filter-tab ${showSubUseCases ? 'active' : ''}`}
          style={{
            padding: '5px 12px',
            fontSize: '0.8rem',
            marginLeft: 'auto',
            borderColor: showSubUseCases ? '#2563EB' : '#CBD5E1',
          }}
          onClick={() => setShowSubUseCases((prev) => !prev)}
        >
          {showSubUseCases
            ? '✓ Đang hiện: Bước xử lý phụ («include» / «extend»)'
            : '+ Hiện thêm bước xử lý phụ («include» / «extend»)'}
        </button>
      </div>

      {/* GIẢI THÍCH NGẮN GỌN KHI BẬT BƯỚC PHỤ INCLUDE / EXTEND */}
      {showSubUseCases && (
        <div
          style={{
            background: '#FFFBEB',
            border: '1px solid #FDE68A',
            borderRadius: '8px',
            padding: '8px 14px',
            marginBottom: '12px',
            fontSize: '0.82rem',
            color: '#92400E',
            display: 'flex',
            gap: '18px',
            flexWrap: 'wrap',
          }}
        >
          <span>
            💡 <strong>Cách đọc ký hiệu UML trên mũi tên nét đứt:</strong>
          </span>
          <span>
            • <code>«include»</code> = <strong>Bước bắt buộc đi kèm</strong> (làm chức năng chính thì luôn chạy bước này)
          </span>
          <span>
            • <code>«extend»</code> = <strong>Bước mở rộng tùy chọn</strong> (chỉ chạy khi người dùng bấm chọn thêm)
          </span>
        </div>
      )}

      {/* KHUNG CÔNG CỤ CHỈNH SỬA & CHẾ ĐỘ NÂNG CAO (CHỈ HIỆN KHI NGƯỜI DÙNG BẤM MỞ) */}
      {showAdvancedTools && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '10px',
            flexWrap: 'wrap',
            background: '#EFF6FF',
            border: '1px solid #BFDBFE',
            borderRadius: '10px',
            padding: '10px 14px',
            marginBottom: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className={`filter-tab ${mode === 'canvas' ? 'active' : ''}`}
              onClick={() => setMode('canvas')}
            >
              1. Bản vẽ Sơ đồ
            </button>
            <button
              type="button"
              className={`filter-tab ${mode === 'mapping' ? 'active' : ''}`}
              onClick={() => setMode('mapping')}
            >
              2. Bảng tổng hợp Người dùng – Chức năng
            </button>
            <button
              type="button"
              className={`filter-tab ${mode === 'code' ? 'active' : ''}`}
              onClick={() => setMode('code')}
            >
              3. Mã kỹ thuật PlantUML (@startuml)
            </button>
          </div>

          {mode === 'canvas' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '6px 11px', fontSize: '0.8rem', background: '#FFFFFF' }}
                onClick={handleAddActor}
              >
                + Thêm Người dùng
              </button>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '6px 11px', fontSize: '0.8rem', background: '#FFFFFF' }}
                onClick={handleAddUseCase}
              >
                + Thêm Chức năng
              </button>
              <button
                type="button"
                className={`btn ${connectMode ? 'btn-primary' : 'btn-outline'}`}
                style={{
                  padding: '6px 11px',
                  fontSize: '0.8rem',
                  background: connectMode ? '#2563EB' : '#FFFFFF',
                }}
                onClick={() =>
                  setConnectMode(
                    connectMode ? null : { step: 'pick-from', type: 'association' }
                  )
                }
              >
                {connectMode ? '✕ Hủy nối dây' : '⎯ Nối thêm dây'}
              </button>

              {connectMode && (
                <select
                  className="select-field"
                  style={{ width: 'auto', padding: '5px 10px', fontSize: '0.8rem' }}
                  value={connectMode.type}
                  onChange={(e) => setConnectMode({ ...connectMode, type: e.target.value })}
                >
                  <option value="association">Nối Người dùng — Chức năng</option>
                  <option value="include">Bước bắt buộc (--«include»--&gt;)</option>
                  <option value="extend">Bước tùy chọn (--«extend»--&gt;)</option>
                </select>
              )}

              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '6px 11px', fontSize: '0.8rem', background: '#FFFFFF' }}
                onClick={handleResetLayout}
              >
                Sắp xếp lại
              </button>
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: '6px 11px', fontSize: '0.8rem', background: '#FFFFFF' }}
                onClick={handleDownloadSvg}
              >
                Tải file Vector (.svg)
              </button>
            </div>
          )}
        </div>
      )}

      {mode === 'canvas' && (
        <div>

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
                ? '👉 Bước 1: Bấm chuột vào hình Bắt đầu (Actor hoặc Use Case) trên bản vẽ...'
                : '👉 Bước 2: Bấm chuột vào hình Use Case Đích để hoàn tất nối dây!'}
            </div>
          )}

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

          {/* DUAL-SIDE STARUML CANVAS (ACTORS ON LEFT & RIGHT, SYSTEM IN CENTER) */}
          <div
            style={{
              position: 'relative',
              background: '#F1F5F9',
              border: '1px solid #CBD5E1',
              borderRadius: '10px',
              padding: '16px',
              overflow: 'auto',
              maxHeight: '720px',
            }}
          >
            {/* NÚT CỘNG / TRỪ ZOOM NỔI TRỰC TIẾP GÓC PHẢI TRÊN BẢNG VẼ */}
            <div
              style={{
                position: 'sticky',
                top: '0px',
                zIndex: 5,
                display: 'flex',
                justifyContent: 'flex-end',
                marginBottom: '8px',
                pointerEvents: 'none',
              }}
            >
              <div
                style={{
                  pointerEvents: 'auto',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'rgba(255, 255, 255, 0.96)',
                  border: '1.5px solid #93C5FD',
                  borderRadius: '999px',
                  padding: '4px 10px',
                  boxShadow: '0 2px 8px rgba(15, 23, 42, 0.12)',
                }}
              >
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#475569' }}>
                  Phóng to / Thu nhỏ:
                </span>
                <button
                  type="button"
                  onClick={() => setZoom((z) => Math.max(0.5, Number((z - 0.15).toFixed(2))))}
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    border: '1px solid #CBD5E1',
                    background: '#F8FAFC',
                    fontWeight: 800,
                    fontSize: '1rem',
                    cursor: 'pointer',
                    lineHeight: 1,
                  }}
                  title="Thu nhỏ (-)"
                >
                  −
                </button>
                <button
                  type="button"
                  onClick={() => setZoom(1)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '999px',
                    border: '1px solid #BFDBFE',
                    background: '#EFF6FF',
                    color: '#1E3A8A',
                    fontWeight: 700,
                    fontSize: '0.78rem',
                    cursor: 'pointer',
                  }}
                  title="Đặt lại vừa khít khung nhìn (100%)"
                >
                  {Math.round(zoom * 100)}%
                </button>
                <button
                  type="button"
                  onClick={() => setZoom((z) => Math.min(2.0, Number((z + 0.15).toFixed(2))))}
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    border: '1px solid #CBD5E1',
                    background: '#F8FAFC',
                    fontWeight: 800,
                    fontSize: '1rem',
                    cursor: 'pointer',
                    lineHeight: 1,
                  }}
                  title="Phóng to (+)"
                >
                  +
                </button>
              </div>
            </div>

            <svg
              ref={svgRef}
              viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
              style={{
                display: 'block',
                width: `${Math.round(zoom * 100)}%`,
                height: 'auto',
                minWidth: zoom > 1 ? `${Math.round(zoom * 100)}%` : '0',
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

              {/* CENTERED SYSTEM BOUNDARY BOX (x = 195..1065, leaving clean gutters for Left Actors at x=92 and Right Actors at x=1168) */}
              <rect
                x="195"
                y="26"
                width="870"
                height={canvasHeight - 52}
                rx="4"
                fill="#FAFAFC"
                stroke="#1E293B"
                strokeWidth="1.8"
              />
              <line
                x1="195"
                y1="64"
                x2="1065"
                y2="64"
                stroke="#CBD5E1"
                strokeWidth="1.2"
              />
              <text
                x="630"
                y="43"
                textAnchor="middle"
                fill="#64748B"
                fontFamily="JetBrains Mono, monospace"
                fontSize="10.5"
              >
                «system»
              </text>
              <text
                x="630"
                y="58"
                textAnchor="middle"
                fill="#0F172A"
                fontFamily="Be Vietnam Pro, Segoe UI, sans-serif"
                fontSize="13.5"
                fontWeight="700"
              >
                {graph.systemTitle}
              </text>

              {/* RELATIONSHIPS */}
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

              {/* ACTORS (LEFT AND RIGHT SIDES) */}
              {graph.actors.map((actor) => {
                const isSel =
                  (selectedItem?.kind === 'actor' && selectedItem?.id === actor.id) ||
                  connectMode?.fromId === actor.id;
                const actorLines = wrapUseCaseText(actor.name, 16);

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
                    <circle
                      cx="0"
                      cy="-22"
                      r="10.5"
                      fill="#FFFFFF"
                      stroke="#0F172A"
                      strokeWidth="2"
                    />
                    <line x1="0" y1="-11.5" x2="0" y2="12" stroke="#0F172A" strokeWidth="2" />
                    <line x1="-16" y1="-2" x2="16" y2="-2" stroke="#0F172A" strokeWidth="2" />
                    <line x1="0" y1="12" x2="-13" y2="31" stroke="#0F172A" strokeWidth="2" />
                    <line x1="0" y1="12" x2="13" y2="31" stroke="#0F172A" strokeWidth="2" />

                    {actorLines.map((ln, idx) => (
                      <text
                        key={idx}
                        x="0"
                        y={48 + idx * 14}
                        textAnchor="middle"
                        fill="#0F172A"
                        fontFamily="Be Vietnam Pro, Segoe UI, sans-serif"
                        fontSize="12"
                        fontWeight="700"
                      >
                        {ln}
                      </text>
                    ))}
                  </g>
                );
              })}

              {/* USE CASES */}
              {graph.useCases.map((uc) => {
                const isSel =
                  (selectedItem?.kind === 'uc' && selectedItem?.id === uc.id) ||
                  connectMode?.fromId === uc.id;
                const { rx, ry, lines } = getEllipseRadii(uc.name);
                const startTextY = -((lines.length - 1) * 14.5) / 2 + 4;

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
                        y={startTextY + idx * 14.5}
                        textAnchor="middle"
                        fill="#0F172A"
                        fontFamily="Be Vietnam Pro, Segoe UI, sans-serif"
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

      {mode === 'mapping' && (
        <div>
          <div
            style={{
              background: '#EFF6FF',
              border: '1px solid #BFDBFE',
              borderRadius: '10px',
              padding: '12px 16px',
              marginBottom: '14px',
              fontSize: '0.88rem',
              color: '#1E3A8A',
            }}
          >
            <strong>Phần 1: Bảng ánh xạ Actor – Use Case chuẩn UML 2.5</strong> — Kiểm chứng tính đầy đủ giữa Tác nhân (Primary / Secondary Actors), Ca sử dụng chính (Động từ + Đối tượng, đã loại bỏ mã FR-xx/UC-xx) và các Ca sử dụng con (<code>«include»</code> / <code>«extend»</code>).
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: `${(0.88 * tableZoom).toFixed(2)}rem`,
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '8px',
              }}
            >
              <thead>
                <tr style={{ background: '#F8FAFC', borderBottom: '2px solid #CBD5E1', textAlign: 'left' }}>
                  <th style={{ padding: '10px 14px', color: '#0F172A' }}>Mã YC</th>
                  <th style={{ padding: '10px 14px', color: '#0F172A' }}>Tác nhân (Actor)</th>
                  <th style={{ padding: '10px 14px', color: '#0F172A' }}>Loại Actor</th>
                  <th style={{ padding: '10px 14px', color: '#0F172A' }}>Use Case Chính (Động từ + Đối tượng)</th>
                  <th style={{ padding: '10px 14px', color: '#0F172A' }}>Use Case Con («include» / «extend»)</th>
                </tr>
              </thead>
              <tbody>
                {allFunctionalStories.map((us, i) => {
                  const roleName = (us.role || 'Người dùng').trim();
                  const isSec = isSecondaryActorRole(roleName);
                  const subs = Array.isArray(us.sub_usecases) ? us.sub_usecases : [];
                  return (
                    <tr key={us.story_id || i} style={{ borderBottom: '1px solid #E2E8F0' }}>
                      <td style={{ padding: '10px 14px', fontWeight: 700, color: '#334155' }}>
                        {us.req_id}
                      </td>
                      <td style={{ padding: '10px 14px', fontWeight: 600, color: '#0F172A' }}>
                        {roleName}
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span
                          className={`badge ${isSec ? 'badge-nfr' : 'badge-fr'}`}
                          style={{ fontSize: '0.75rem' }}
                        >
                          {isSec ? 'Secondary (Bên phải)' : 'Primary (Bên trái)'}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px', fontWeight: 700, color: '#1E3A8A' }}>
                        {stripUseCasePrefixAndActor(us.puml_usecase_name)}
                      </td>
                      <td style={{ padding: '10px 14px', color: '#475569' }}>
                        {subs.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {subs.map((s, sIdx) => (
                              <span key={sIdx} style={{ fontSize: '0.82rem' }}>
                                <code
                                  style={{
                                    background: '#F1F5F9',
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                    color: '#0F172A',
                                    marginRight: '6px',
                                  }}
                                >
                                  {`«${s.rel_type || 'include'}»`}
                                </code>
                                {stripUseCasePrefixAndActor(s.target_name)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span style={{ color: '#94A3B8', fontSize: '0.8rem' }}>—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

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

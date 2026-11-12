import {createVoiceCoach} from "./voice_coach.mjs";

const FRAME_BATCH_INTERVAL_MS = 200;
const FRAME_STALL_TIMEOUT_MS = 600;
const MIN_DETECT_INTERVAL_MS = 50;
const ACK_TIMEOUT_MS = 1200;
const get = id => document.getElementById(id);
const setStatus = text => {
  const el = get("status");
  if (el.textContent !== text) el.textContent = text;
};
const video = get("input"), canvas = get("view"), ctx = canvas.getContext("2d");
const joints = [
  ["Khuỷu trái", 11, 13, 15], ["Khuỷu phải", 12, 14, 16],
  ["Gối trái", 23, 25, 27], ["Gối phải", 24, 26, 28]
];
const labels = joints.map(() => get("angles").appendChild(document.createElement("span")));
let encodedModel, decodedModelBytes, detector, connections, stream, animation, isStarting = false, showMetrics = true;
const observesVideoFrames = typeof video.requestVideoFrameCallback === "function";
let sessionId, frameCount, windowStart, lastFrameAt;
let videoFrameCallback, presentedFrame, lastDrawnFrame;
let pendingFrames = [], frameSequence = 0, lastBatchAt = 0, cameraRun = 0;
let awaitingAckSequence = null, awaitingAckSince = 0;
let lastDetectAt = -Infinity, lastPose = [], lastFrameHeight = 0;
let trackingInterrupted = true;
const streamId = globalThis.crypto?.randomUUID?.() ??
  `${Date.now()}-${Math.random().toString(36).slice(2)}`;
let lastVoiceSequence = 0;
const voiceButton = get("voice");
const cameraDevice = get("camera-device");
const mediaDevices = navigator.mediaDevices;

function applyMetricsVisibility(visible) {
  showMetrics = visible !== false;
  get("fps").hidden = !showMetrics;
  get("angles").hidden = !showMetrics;
}

function updateToggleButton(isRunning) {
  const btn = get("camera-toggle");
  btn.textContent = isRunning ? "⏹ Tắt camera" : "📷 Bật camera";
  btn.setAttribute("aria-pressed", String(Boolean(isRunning)));
  btn.disabled = isStarting || (!isRunning && (!encodedModel || !mediaDevices?.getUserMedia));
}
const cameraErrors = {
  NotAllowedError: "Trình duyệt hoặc hệ điều hành đang chặn camera. Hãy kiểm tra quyền camera cho trang này rồi thử lại.",
  NotFoundError: "Không tìm thấy camera. Hãy kết nối camera hoặc chọn Chế độ Tự do trong phòng tập.",
  NotReadableError: "Không đọc được camera. Hãy kiểm tra kết nối và đóng ứng dụng khác đang dùng camera.",
  OverconstrainedError: "Camera đã chọn không còn khả dụng. Hãy chọn thiết bị khác rồi thử lại.",
};
const voiceCoach = createVoiceCoach({
  AudioContext: window.AudioContext ?? window.webkitAudioContext,
  showCue: text => { get("voice-cue").textContent = text; },
  showStatus: text => { get("voice-status").textContent = text; },
  onEnabledChange: enabled => {
    get("voice-icon").textContent = enabled ? "🔊" : "🔇";
    voiceButton.setAttribute("aria-pressed", String(enabled));
  },
  onCorrection: (event, decision) => {
    console.debug("Voice Coach squat nông", {frame: event.frame_sequence, decision});
  },
});
voiceButton.disabled = !voiceCoach.supported;
if (!voiceCoach.supported) {
  get("voice-status").textContent = "Trình duyệt này không hỗ trợ phát giọng nói.";
}
voiceButton.onclick = () => voiceCoach.toggle();

function send(type, data) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...data}, location.origin);
}

async function refreshCameraDevices() {
  if (!mediaDevices?.enumerateDevices) return;
  try {
    const devices = await mediaDevices.enumerateDevices();
    const cameras = devices.filter(device => device.kind === "videoinput" && device.deviceId);
    const selected = cameraDevice.value;
    cameraDevice.replaceChildren(new Option("Mặc định của trình duyệt", ""));
    cameras.forEach((camera, index) => {
      cameraDevice.add(new Option(camera.label || `Camera ${index + 1}`, camera.deviceId));
    });
    if (cameras.some(camera => camera.deviceId === selected)) cameraDevice.value = selected;
  } catch {
    // The browser's default camera remains available even if listing devices fails.
  }
}

const setupTimer = window.parent === window ? null : setTimeout(() => {
  get("status").textContent = "Chưa nhận được dữ liệu camera từ FitSense. Hãy tải lại trang phòng tập.";
}, 8000);
if (window.parent === window) {
  get("status").textContent = "Hãy mở Phòng tập Trực tiếp trong app FitSense để dùng camera. Trang này cần dữ liệu từ app.";
}
window.addEventListener("message", event => {
  if (event.source !== parent || event.origin !== location.origin ||
      event.data?.type !== "streamlit:render") return;
  const {model, session_id: renderSessionId, last_event_id: acknowledged, voice_feedback: feedback, show_metrics: visibleMetrics} = event.data.args;
  applyMetricsVisibility(visibleMetrics);
  if (!encodedModel && model && renderSessionId) {
    encodedModel = model;
    sessionId = renderSessionId;
    frameSequence = acknowledged ?? 0;
    clearTimeout(setupTimer);
    if (!mediaDevices?.getUserMedia) {
      get("status").textContent = window.isSecureContext
        ? "Trình duyệt này không mở được camera. Hãy thử Chrome, Edge hoặc Chế độ Tự do."
        : "Camera cần HTTPS hoặc localhost. Hãy mở FitSense qua một trong hai địa chỉ này.";
      return;
    }
    updateToggleButton(Boolean(stream));
    cameraDevice.disabled = false;
    get("status").textContent = "Sẵn sàng bật camera.";
    void refreshCameraDevices();
  }

  if (renderSessionId !== sessionId) return;
  if (Number.isInteger(acknowledged) && acknowledged <= frameSequence) {
    const received = pendingFrames.length - (frameSequence - acknowledged);
    if (received > 0) pendingFrames.splice(0, received);
  }
  if (Number.isInteger(acknowledged) && awaitingAckSequence !== null && acknowledged >= awaitingAckSequence) {
    awaitingAckSequence = null;
  }
  if (!detector || feedback?.session_id !== sessionId || feedback.stream_id !== streamId ||
      feedback.sequence <= lastVoiceSequence) return;
  lastVoiceSequence = feedback.sequence;
  if (feedback.stopped || feedback.interrupted) {
    voiceCoach.stop();
    get("voice-cue").textContent = "";
  }
  if (!feedback.stopped) voiceCoach.receiveBatch(feedback.events ?? []);
});
if (window.parent !== window) {
  send("streamlit:componentReady", {apiVersion: 1});
  new ResizeObserver(() => {
    const height = document.body.offsetHeight + 2;
    if (Math.abs(height - lastFrameHeight) >= 2) {
      lastFrameHeight = height;
      send("streamlit:setFrameHeight", {height});
    }
  }).observe(document.body);
}
mediaDevices?.addEventListener("devicechange", refreshCameraDevices);

function updateAngles(points) {
  joints.forEach(([label, a, b, c], i) => {
    let value = "—";
    if (points[a] && points[b] && points[c]) {
      const ux = points[a].x - points[b].x, uy = points[a].y - points[b].y;
      const vx = points[c].x - points[b].x, vy = points[c].y - points[b].y;
      if ((ux || uy) && (vx || vy)) {
        value = Math.round(Math.atan2(Math.abs(ux*vy - uy*vx), ux*vx + uy*vy) * 180 / Math.PI) + "°";
      }
    }
    labels[i].textContent = label + ": " + value;
  });
}
function angleAt(a, b, c) {
  if (!a || !b || !c) return null;
  const ux = a.x - b.x, uy = a.y - b.y;
  const vx = c.x - b.x, vy = c.y - b.y;
  if ((!ux && !uy) || (!vx && !vy)) return null;
  return Math.atan2(Math.abs(ux*vy - uy*vx), ux*vx + uy*vy) * 180 / Math.PI;
}
function getPoseFeatures(pose) {
  const nose = pose[0];
  const leftShoulder = pose[11], rightShoulder = pose[12];
  const leftElbow = pose[13], rightElbow = pose[14];
  const leftWrist = pose[15], rightWrist = pose[16];
  const leftHip = pose[23], rightHip = pose[24];
  const leftKnee = pose[25], rightKnee = pose[26];
  const leftAnkle = pose[27], rightAnkle = pose[28];

  const kneeAngles = [
    angleAt(leftHip, leftKnee, leftAnkle),
    angleAt(rightHip, rightKnee, rightAnkle)
  ].filter(Number.isFinite);
  const kneeAngle = kneeAngles.length
    ? kneeAngles.reduce((total, angle) => total + angle, 0) / kneeAngles.length
    : null;

  let startDetected = false;
  if (nose && (leftHip || rightHip)) {
    const hips = [leftHip, rightHip].filter(Boolean);
    const bodyHeight = Math.abs(hips.reduce((sum, hip) => sum + hip.y, 0) / hips.length - nose.y);
    if (bodyHeight > 0) {
      startDetected = [
        [leftWrist, leftElbow, leftShoulder, leftHip],
        [rightWrist, rightElbow, rightShoulder, rightHip]
      ].some(([wrist, elbow, shoulder, hip]) =>
        wrist && angleAt(elbow, shoulder, hip) >= 140 &&
        wrist.y < nose.y - 0.15 * bodyHeight
      );
    }
  }

  let xDetected = false;
  if (leftWrist && rightWrist && leftShoulder && rightShoulder && leftHip && rightHip) {
    const shoulderY = (leftShoulder.y + rightShoulder.y) / 2;
    const hipY = (leftHip.y + rightHip.y) / 2;
    const bodyWidth = Math.abs(rightShoulder.x - leftShoulder.x);
    xDetected = bodyWidth > 0 &&
      shoulderY < leftWrist.y && leftWrist.y < hipY &&
      shoulderY < rightWrist.y && rightWrist.y < hipY &&
      Math.abs(leftWrist.x - rightWrist.x) < 0.08 * bodyWidth;
  }

  return {
    knee_angle: kneeAngle,
    start_detected: startDetected,
    x_detected: xDetected,
    head_detected: Boolean(nose)
  };
}
function queueFrame(frame) {
  pendingFrames.push(frame);
  if (pendingFrames.length > 100) pendingFrames.shift();
  frameSequence++;
}
function sendFrameBatch(force = false, now = performance.now()) {
  if (!pendingFrames.length) return;
  if (!force && awaitingAckSequence !== null && now - awaitingAckSince < ACK_TIMEOUT_MS) return;
  if (!force) {
    awaitingAckSequence = frameSequence;
    awaitingAckSince = now;
  }
  send("streamlit:setComponentValue", {
    value: {session_id: sessionId, stream_id: streamId, sequence: frameSequence, frames: pendingFrames},
    dataType: "json"
  });
}
function sendTrackingLoss() {
  trackingInterrupted = true;
  queueFrame({...getPoseFeatures([]), tracking_interrupted: true});
  lastVoiceSequence = frameSequence;
  voiceCoach.stop();
  get("voice-cue").textContent = "";
  sendFrameBatch(true);
}
function stopCamera(message = "Đã tắt camera.") {
  cameraRun++;
  isStarting = false;
  if (stream) sendTrackingLoss();
  else voiceCoach.stop();
  awaitingAckSequence = null;
  awaitingAckSince = 0;
  lastDetectAt = -Infinity;
  lastPose = [];
  cancelAnimationFrame(animation);
  if (videoFrameCallback !== undefined) video.cancelVideoFrameCallback(videoFrameCallback);
  videoFrameCallback = undefined;
  stream?.getTracks().forEach(track => track.stop());
  stream = null;
  video.srcObject = null;
  detector?.close();
  detector = null;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  updateToggleButton(false);
  cameraDevice.disabled = !encodedModel || !mediaDevices?.getUserMedia;
  setStatus(message);
  get("fps").textContent = "FPS: —";
  updateAngles([]);
}
function observeVideoFrame(_now, metadata) {
  presentedFrame = metadata.presentedFrames;
  videoFrameCallback = video.requestVideoFrameCallback(observeVideoFrame);
}
function draw(now) {
  try {
    if (!trackingInterrupted && now - lastFrameAt >= FRAME_STALL_TIMEOUT_MS) {
      sendTrackingLoss();
      setStatus("Camera chưa gửi khung hình mới. Phiên tập đang tạm dừng.");
    }
    const frame = observesVideoFrames ? presentedFrame : video.currentTime;
    if (video.readyState >= 2 && frame !== undefined && frame !== lastDrawnFrame) {
      lastDrawnFrame = frame;
      lastFrameAt = now;
      trackingInterrupted = false;
      const shouldDetect = now - lastDetectAt >= MIN_DETECT_INTERVAL_MS;
      if (shouldDetect) {
        lastDetectAt = now;
        lastPose = detector.detectForVideo(video, now).landmarks[0] ?? [];
      }
      const pose = lastPose;
      const w = video.videoWidth, h = video.videoHeight;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w; canvas.height = h;
      }
      ctx.drawImage(video, 0, 0, w, h);
      const points = pose.map(p => p.visibility >= 0.5 ? {x:p.x*w, y:p.y*h} : null);
      if (connections.length) {
        ctx.strokeStyle = "#60ed86"; ctx.lineWidth = 2;
        ctx.beginPath();
        for (const {start, end} of connections) {
          const a = points[start], b = points[end];
          if (!a || !b) continue;
          ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
        }
        ctx.stroke();
      }
      ctx.fillStyle = "#ffbe36";
      for (const p of points.filter(Boolean)) {
        ctx.beginPath(); ctx.arc(p.x,p.y,3,0,Math.PI*2); ctx.fill();
      }
      if (shouldDetect) {
        if (showMetrics) updateAngles(points);
        const features = getPoseFeatures(points);
        const hand = features.start_detected ? "Đã thấy tay giơ cao" : "Chưa thấy tay giơ cao";
        const knee = features.knee_angle === null ? "chưa thấy rõ chân" : Math.round(features.knee_angle) + "°";
        setStatus(pose.length ? hand + " · Góc gối dùng để đếm: " + knee : "Hãy đứng trong khung hình.");
        queueFrame({...features, captured_at: now});
      }
      if (now - lastBatchAt >= FRAME_BATCH_INTERVAL_MS) {
        lastBatchAt = now;
        sendFrameBatch(false, now);
      }
      frameCount++;
      if (now - windowStart >= 1000) {
        if (showMetrics) {
          get("fps").textContent = "FPS: " + (1000*frameCount/(now-windowStart)).toFixed(1);
        }
        frameCount = 0; windowStart = now;
      }
    }
    animation = requestAnimationFrame(draw);
  } catch (err) { stopCamera("Lỗi xử lý hình: " + err.message); }
}
// Luôn lật gương mặc định 1 lần (đã bỏ nút chuyển chế độ gương thủ công)
canvas.style.transform = "scaleX(-1)";
get("camera-toggle").onclick = async () => {
  if (stream || isStarting) {
    stopCamera();
    return;
  }
  const run = ++cameraRun;
  isStarting = true;
  const btn = get("camera-toggle");
  btn.disabled = true;
  btn.textContent = "⏳ Đang bật camera…";
  cameraDevice.disabled = true;
  setStatus("Đang mở camera và nạp model…");
  try {
    const constraints = {width: {ideal: 640}, height: {ideal: 480}, frameRate: {ideal: 20}};
    if (cameraDevice.value) constraints.deviceId = {exact: cameraDevice.value};
    const openedStream = await mediaDevices.getUserMedia({video: constraints, audio: false});
    if (run !== cameraRun) {
      openedStream.getTracks().forEach(track => track.stop());
      return;
    }
    stream = openedStream;
    void refreshCameraDevices();
    stream.getVideoTracks()[0].onended = () => {
      if (run === cameraRun) stopCamera("Camera đã ngắt kết nối.");
    };
    video.srcObject = stream;
    await video.play();
    const {FilesetResolver, PoseLandmarker} = await import("./vendor/mediapipe/vision_bundle.mjs");
    const files = await FilesetResolver.forVisionTasks(new URL("./vendor/mediapipe/wasm", location.href).href);
    if (!decodedModelBytes) {
      decodedModelBytes = Uint8Array.from(atob(encodedModel), c => c.charCodeAt(0));
    }
    let loadedDetector;
    try {
      loadedDetector = await PoseLandmarker.createFromOptions(files, {
        baseOptions:{modelAssetBuffer:decodedModelBytes.slice(), delegate:"GPU"},
        runningMode:"VIDEO", numPoses:1
      });
    } catch {
      loadedDetector = await PoseLandmarker.createFromOptions(files, {
        baseOptions:{modelAssetBuffer:decodedModelBytes.slice()},
        runningMode:"VIDEO", numPoses:1
      });
    }
    if (run !== cameraRun) {
      loadedDetector.close();
      return;
    }
    detector = loadedDetector;
    connections = PoseLandmarker.POSE_CONNECTIONS;
    frameCount = 0;
    presentedFrame = lastDrawnFrame = undefined;
    awaitingAckSequence = null;
    awaitingAckSince = 0;
    lastDetectAt = -Infinity;
    lastPose = [];
    windowStart = performance.now();
    lastFrameAt = lastBatchAt = windowStart;
    sendTrackingLoss();
    isStarting = false;
    updateToggleButton(true);
    if (observesVideoFrames) videoFrameCallback = video.requestVideoFrameCallback(observeVideoFrame);
    animation = requestAnimationFrame(draw);
  } catch (err) {
    if (run !== cameraRun) return;
    stopCamera(cameraErrors[err.name] ?? "Không mở được camera: " + err.message);
    void refreshCameraDevices();
  }
};
window.addEventListener("pagehide", () => stopCamera());
updateAngles([]);

import {createVoiceCoach} from "./voice_coach.mjs";

const get = id => document.getElementById(id);
const video = get("input"), canvas = get("view"), ctx = canvas.getContext("2d");
const joints = [
  ["Khuỷu trái", 11, 13, 15], ["Khuỷu phải", 12, 14, 16],
  ["Gối trái", 23, 25, 27], ["Gối phải", 24, 26, 28]
];
const labels = joints.map(() => get("angles").appendChild(document.createElement("span")));
let encodedModel, detector, connections, stream, animation, mirrored = true;
let lastVideoTime, frameCount, windowStart;
let pendingFrames = [], batchSequence = 0, lastBatchAt = 0;
const streamId = globalThis.crypto?.randomUUID?.() ??
  `${Date.now()}-${Math.random().toString(36).slice(2)}`;
let lastVoiceSequence = 0;
const voiceButton = get("voice");
const cameraDevice = get("camera-device");
const mediaDevices = navigator.mediaDevices;
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
});
voiceButton.disabled = !voiceCoach.supported;
if (!voiceCoach.supported) {
  get("voice-status").textContent = "Trình duyệt này không hỗ trợ phát giọng nói.";
}
voiceButton.onclick = () => {
  voiceCoach.toggle();
  voiceButton.setAttribute("aria-pressed", String(voiceCoach.enabled));
};

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
  const {model, voice_feedback: feedback} = event.data.args;
  if (!encodedModel && model) {
    encodedModel = model;
    clearTimeout(setupTimer);
    if (!mediaDevices?.getUserMedia) {
      get("status").textContent = window.isSecureContext
        ? "Trình duyệt này không mở được camera. Hãy thử Chrome, Edge hoặc Chế độ Tự do."
        : "Camera cần HTTPS hoặc localhost. Hãy mở FitSense qua một trong hai địa chỉ này.";
      return;
    }
    get("start").disabled = false;
    cameraDevice.disabled = false;
    get("status").textContent = "Sẵn sàng bật camera.";
    void refreshCameraDevices();
  }

  if (!detector) return;
  if (!feedback) {
    if (lastVoiceSequence > 0) voiceCoach.stop();
    get("voice-cue").textContent = "";
    return;
  }
  if (feedback.stream_id !== streamId || feedback.sequence <= lastVoiceSequence) return;
  lastVoiceSequence = feedback.sequence;
  if (feedback.stopped) {
    voiceCoach.stop();
    get("voice-cue").textContent = "";
  } else {
    voiceCoach.receive(feedback.event);
  }
});
if (window.parent !== window) {
  send("streamlit:componentReady", {apiVersion: 1});
  new ResizeObserver(() => send("streamlit:setFrameHeight", {height: document.body.offsetHeight + 2}))
    .observe(document.body);
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
function sendFrameBatch() {
  if (!pendingFrames.length) return;
  const frames = pendingFrames;
  pendingFrames = [];
  send("streamlit:setComponentValue", {
    value: {stream_id: streamId, sequence: ++batchSequence, frames},
    dataType: "json"
  });
}
function stopCamera(message = "Đã tắt camera.") {
  voiceCoach.stop();
  lastVoiceSequence = batchSequence;
  get("voice-cue").textContent = "";
  cancelAnimationFrame(animation);
  stream?.getTracks().forEach(track => track.stop());
  stream = null;
  video.srcObject = null;
  detector?.close();
  detector = null;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  get("start").disabled = !encodedModel || !mediaDevices?.getUserMedia;
  cameraDevice.disabled = get("start").disabled;
  get("stop").disabled = true;
  get("status").textContent = message;
  get("fps").textContent = "FPS: —";
  updateAngles([]);
}
function draw(now) {
  try {
    if (video.readyState >= 2 && video.currentTime !== lastVideoTime) {
      lastVideoTime = video.currentTime;
      const pose = detector.detectForVideo(video, now).landmarks[0] ?? [];
      const w = video.videoWidth, h = video.videoHeight;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w; canvas.height = h;
      }
      ctx.drawImage(video, 0, 0, w, h);
      const points = pose.map(p => p.visibility >= 0.5 ? {x:p.x*w, y:p.y*h} : null);
      ctx.strokeStyle = "#60ed86"; ctx.lineWidth = 2;
      for (const {start, end} of connections) {
        const a = points[start], b = points[end];
        if (!a || !b) continue;
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
      }
      ctx.fillStyle = "#ffbe36";
      for (const p of points.filter(Boolean)) {
        ctx.beginPath(); ctx.arc(p.x,p.y,3,0,Math.PI*2); ctx.fill();
      }
      updateAngles(points);
      const features = getPoseFeatures(points);
      const hand = features.start_detected ? "Đã thấy tay giơ cao" : "Chưa thấy tay giơ cao";
      const knee = features.knee_angle === null ? "chưa thấy rõ chân" : Math.round(features.knee_angle) + "°";
      get("status").textContent = pose.length ? hand + " · Góc gối dùng để đếm: " + knee : "Hãy đứng trong khung hình.";
      pendingFrames.push({...features, captured_at: now});
      if (now - lastBatchAt >= 200) {
        lastBatchAt = now;
        sendFrameBatch();
      }
      frameCount++;
      if (now - windowStart >= 1000) {
        get("fps").textContent = "FPS: " + (1000*frameCount/(now-windowStart)).toFixed(1);
        frameCount = 0; windowStart = now;
      }
    }
    animation = requestAnimationFrame(draw);
  } catch (err) { stopCamera("Lỗi xử lý hình: " + err.message); }
}
canvas.style.transform = "scaleX(-1)";
get("mirror").onclick = () => {
  mirrored = !mirrored;
  canvas.style.transform = mirrored ? "scaleX(-1)" : "";
  get("mirror").setAttribute("aria-pressed", String(mirrored));
};
get("start").onclick = async () => {
  get("start").disabled = true;
  cameraDevice.disabled = true;
  get("status").textContent = "Đang mở camera và nạp model…";
  try {
    const constraints = {width: {ideal: 640}, height: {ideal: 480}};
    if (cameraDevice.value) constraints.deviceId = {exact: cameraDevice.value};
    stream = await mediaDevices.getUserMedia({video: constraints, audio: false});
    void refreshCameraDevices();
    stream.getVideoTracks()[0].onended = () => stopCamera("Camera đã ngắt kết nối.");
    video.srcObject = stream;
    await video.play();
    const {FilesetResolver, PoseLandmarker} = await import("./vendor/mediapipe/vision_bundle.mjs");
    const files = await FilesetResolver.forVisionTasks(new URL("./vendor/mediapipe/wasm", location.href).href);
    detector = await PoseLandmarker.createFromOptions(files, {
      baseOptions:{modelAssetBuffer:Uint8Array.from(atob(encodedModel), c => c.charCodeAt(0))},
      runningMode:"VIDEO", numPoses:1
    });
    connections = PoseLandmarker.POSE_CONNECTIONS;
    frameCount = 0; lastVideoTime = -1; windowStart = performance.now();
    pendingFrames = []; lastBatchAt = windowStart;
    get("stop").disabled = false;
    animation = requestAnimationFrame(draw);
  } catch (err) {
    stopCamera(cameraErrors[err.name] ?? "Không mở được camera: " + err.message);
    void refreshCameraDevices();
  }
};
get("stop").onclick = () => {
  sendFrameBatch();
  stopCamera();
};
window.addEventListener("pagehide", () => stopCamera());
updateAngles([]);

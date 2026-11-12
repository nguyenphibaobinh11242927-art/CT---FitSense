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
let encodedModel, detector, connections, stream, animation, mirrored = true;
let lastVideoTime, frameCount, windowStart;
let pendingFrames = [], batchSequence = 0, lastBatchAt = 0;
const streamId = globalThis.crypto?.randomUUID?.() ??
  `${Date.now()}-${Math.random().toString(36).slice(2)}`;

function send(type, data) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...data}, location.origin);
}
window.addEventListener("message", event => {
  if (event.source !== parent || event.origin !== location.origin ||
      event.data?.type !== "streamlit:render") return;
  if (encodedModel) return;
  encodedModel = event.data.args.model;

  get("start").disabled = false;
  if (!stream) get("status").textContent = "Sẵn sàng bật camera.";
});
send("streamlit:componentReady", {apiVersion: 1});
new ResizeObserver(() => send("streamlit:setFrameHeight", {height: document.body.offsetHeight + 2}))
  .observe(document.body);

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

function getPoseFeatures(pose, width, height) {
  const points = pose.map(point => point && point.visibility >= 0.5
    ? {x: point.x * width, y: point.y * height}
    : null);
  const nose = points[0];
  const leftShoulder = points[11], rightShoulder = points[12];
  const leftElbow = points[13], rightElbow = points[14];
  const leftWrist = points[15], rightWrist = points[16];
  const leftHip = points[23], rightHip = points[24];
  const leftKnee = points[25], rightKnee = points[26];
  const leftAnkle = points[27], rightAnkle = points[28];
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
      Math.abs(leftWrist.x - rightWrist.x) < 0.15 * bodyWidth;
  }

  return {
    points,
    tracked: Boolean(nose && leftShoulder && rightShoulder && (leftHip || rightHip)),
    head_visible: Boolean(nose),
    knee_angle: kneeAngle,
    start_detected: startDetected,
    x_detected: xDetected
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
      for (const point of features.points.filter(Boolean)) {
        ctx.beginPath();
        ctx.arc(point.x, point.y, 3, 0, Math.PI * 2);
        ctx.fill();
      }
      updateAngles(points);
      const features = getPoseFeatures(points);
      const hand = features.start_detected ? "Đã thấy tay giơ cao" : "Chưa thấy tay giơ cao";
      const knee = features.knee_angle === null ? "chưa thấy rõ chân" : Math.round(features.knee_angle) + "°";
      get("status").textContent = pose.length ? hand + " · Góc gối dùng để đếm: " + knee : "Hãy đứng trong khung hình.";
      pendingFrames.push(features);
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
  } catch (error) {
    stopCamera("Lỗi xử lý hình: " + error.message);
  }
}
canvas.style.transform = "scaleX(-1)";
get("mirror").onclick = () => {
  mirrored = !mirrored;
  canvas.style.transform = mirrored ? "scaleX(-1)" : "";
  get("mirror").setAttribute("aria-pressed", String(mirrored));
};
get("start").onclick = async () => {
  get("start").disabled = true;
  get("status").textContent = "Đang mở camera và nạp model…";
  try {
    stream = await navigator.mediaDevices.getUserMedia({video: {width:{ideal:640}, height:{ideal:480}}, audio:false});
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
    stopCamera(err.name === "NotAllowedError" ? "Hãy cho phép camera trong trình duyệt rồi bật lại." :
      "Không mở được camera: " + err.message);
  }
};
get("stop").onclick = () => {
  sendFrameBatch();
  stopCamera();
};
window.addEventListener("pagehide", () => stopCamera());
updateAngles([]);

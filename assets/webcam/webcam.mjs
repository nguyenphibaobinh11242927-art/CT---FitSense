const get = id => document.getElementById(id);
const video = get("input"), canvas = get("view"), ctx = canvas.getContext("2d");
const joints = [
  ["Khuỷu trái", 11, 13, 15], ["Khuỷu phải", 12, 14, 16],
  ["Gối trái", 23, 25, 27], ["Gối phải", 24, 26, 28]
];
const labels = joints.map(() => get("angles").appendChild(document.createElement("span")));
let encodedModel, detector, connections, stream, animation, mirrored = true;
let lastVideoTime, frameCount, windowStart;

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
function stopCamera(message = "Đã tắt camera.") {
  cancelAnimationFrame(animation);
  stream?.getTracks().forEach(track => track.stop());
  stream = null;
  video.srcObject = null;
  detector?.close();
  detector = null;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  get("start").disabled = !encodedModel;
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
      get("status").textContent = pose.length ? "Đang theo dõi" : "Hãy đứng trong khung hình.";
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
    get("stop").disabled = false;
    animation = requestAnimationFrame(draw);
  } catch (err) {
    stopCamera(err.name === "NotAllowedError" ? "Hãy cho phép camera trong trình duyệt rồi bật lại." :
      "Không mở được camera: " + err.message);
  }
};
get("stop").onclick = () => stopCamera();
window.addEventListener("pagehide", () => stopCamera());
updateAngles([]);

// Screen-context capture (screenshots of your screen for problem context) and
// video frame extraction (for "describe this video"). Both produce
// { mediaType, base64 } objects ready to send to a multimodal LLM.

function canvasToImage(canvas, quality = 0.85) {
  const dataUrl = canvas.toDataURL("image/jpeg", quality);
  const base64 = dataUrl.split(",")[1];
  return { mediaType: "image/jpeg", base64, dataUrl };
}

// Grab a single still frame of the user's screen / a window / a tab.
// Returns one image object. Throws if the user cancels the picker.
export async function captureScreenshot() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
    throw new Error("Screen capture isn't supported here (desktop Chrome/Edge only).");
  }
  const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
  try {
    const track = stream.getVideoTracks()[0];
    const video = document.createElement("video");
    video.srcObject = stream;
    await video.play();
    // Give the frame a tick to paint.
    await new Promise((r) => setTimeout(r, 200));

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    track.stop();
    return canvasToImage(canvas);
  } finally {
    stream.getTracks().forEach((t) => t.stop());
  }
}

// Extract `count` evenly-spaced frames from a video File/Blob.
// Returns an array of image objects. Used by the "describe video" mode.
export async function extractVideoFrames(file, count = 6, maxDim = 768) {
  const url = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.src = url;
  video.muted = true;
  video.crossOrigin = "anonymous";

  await new Promise((resolve, reject) => {
    video.onloadedmetadata = resolve;
    video.onerror = () => reject(new Error("Could not load that video file."));
  });

  const duration = video.duration || 0;
  if (!isFinite(duration) || duration <= 0) {
    URL.revokeObjectURL(url);
    throw new Error("Could not read the video's duration.");
  }

  const scale = Math.min(1, maxDim / Math.max(video.videoWidth, video.videoHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(video.videoWidth * scale);
  canvas.height = Math.round(video.videoHeight * scale);
  const ctx = canvas.getContext("2d");

  const frames = [];
  for (let i = 0; i < count; i++) {
    // Sample from ~5% to ~95% of the timeline so we skip dead intro/outro frames.
    const t = duration * (0.05 + (0.9 * i) / Math.max(1, count - 1));
    await seek(video, t);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    frames.push(canvasToImage(canvas, 0.8));
  }

  URL.revokeObjectURL(url);
  return frames;
}

function seek(video, time) {
  return new Promise((resolve) => {
    const onSeeked = () => {
      video.removeEventListener("seeked", onSeeked);
      resolve();
    };
    video.addEventListener("seeked", onSeeked);
    video.currentTime = Math.min(time, Math.max(0, video.duration - 0.05));
  });
}

// Record microphone audio. Used by the "record → auto-send" flow; we run live
// transcription alongside, so this mainly drives the record button's state.
export class AudioRecorder {
  constructor() {
    this.stream = null;
    this.recorder = null;
    this.chunks = [];
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.chunks = [];
    this.recorder = new MediaRecorder(this.stream);
    this.recorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.chunks.push(e.data);
    };
    this.recorder.start();
  }

  async stop() {
    return new Promise((resolve) => {
      if (!this.recorder) return resolve(null);
      this.recorder.onstop = () => {
        const blob = new Blob(this.chunks, { type: "audio/webm" });
        this.stream.getTracks().forEach((t) => t.stop());
        resolve(blob);
      };
      this.recorder.stop();
    });
  }
}

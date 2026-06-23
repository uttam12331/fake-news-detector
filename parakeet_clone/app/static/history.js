// Meeting history: groups every Q&A exchange into a "meeting" the user can
// browse later. Persisted in localStorage. We deliberately do NOT keep the
// raw screenshot image data here (it would blow the localStorage quota fast)
// — only a count of how many screenshots were attached to each entry.

const KEY = "cl_meetings";
const MAX_MEETINGS = 50;

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch (_) {
    return [];
  }
}

function save(meetings) {
  // Keep storage bounded: drop the oldest meetings once we exceed the cap.
  const trimmed = meetings.slice(-MAX_MEETINGS);
  localStorage.setItem(KEY, JSON.stringify(trimmed));
  return trimmed;
}

export function listMeetings() {
  return load().slice().reverse(); // newest first
}

export function getMeeting(id) {
  return load().find((m) => m.id === id) || null;
}

function makeTitle(date) {
  return `Meeting — ${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

export function startNewMeeting() {
  const meetings = load();
  const id = `m_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const meeting = { id, title: makeTitle(new Date()), startedAt: Date.now(), entries: [] };
  meetings.push(meeting);
  save(meetings);
  return meeting;
}

export function getOrCreateCurrentMeeting() {
  const meetings = load();
  if (meetings.length > 0) return meetings[meetings.length - 1];
  return startNewMeeting();
}

// entry: { question, answerRaw, screenshotCount, hasCode, verified, mode }
export function addEntry(meetingId, entry) {
  const meetings = load();
  const meeting = meetings.find((m) => m.id === meetingId);
  if (!meeting) return;
  meeting.entries.push({ ts: Date.now(), ...entry });
  save(meetings);
}

export function renameMeeting(meetingId, title) {
  const meetings = load();
  const meeting = meetings.find((m) => m.id === meetingId);
  if (!meeting) return;
  meeting.title = title || meeting.title;
  save(meetings);
}

export function deleteMeeting(meetingId) {
  const meetings = load().filter((m) => m.id !== meetingId);
  save(meetings);
}

export function clearAllMeetings() {
  localStorage.removeItem(KEY);
}

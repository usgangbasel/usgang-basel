// Backend for the GitHub-hosted version of Ausgang Basel.
// Provides the same small API the page used inside Claude (claude.use("db"/"user")),
// backed by static JSON files (events, venues) plus Firebase Firestore (votes, submissions, requests, venue edits).
(function(){
  const firebaseConfig = {
    apiKey: "AIzaSyDByQMcYoP08btNM1vIyF4Xak37I9oDIkQ",
    authDomain: "usgangbasel-2cf6e.firebaseapp.com",
    projectId: "usgangbasel-2cf6e",
    storageBucket: "usgangbasel-2cf6e.firebasestorage.app",
    messagingSenderId: "596554680467",
    appId: "1:596554680467:web:f173bc21b8a8bfe3aa2566"
  };
  window.NO_VENUE_REQUESTS = true; // no processor for venue requests in the hosted version yet

  let fs = null, auth = null;
  try {
    firebase.initializeApp(firebaseConfig);
    fs = firebase.firestore();
    auth = firebase.auth();
  } catch (e) { console.error("Firebase init failed", e); }

  const ready = new Promise(resolve => {
    if (!auth) return resolve(null);
    let done = false;
    auth.onAuthStateChanged(u => {
      if (u){ if (!done){ done = true; resolve(u); } }
      else auth.signInAnonymously().catch(err => { console.error("Anonymous sign-in failed", err); if (!done){ done = true; resolve(null); } });
    });
  });

  const fileCache = {};
  const loadFile = name => fileCache[name] || (fileCache[name] = fetch(`data/${name}.json`, {cache:"no-cache"}).then(r => r.ok ? r.json() : {}).catch(() => ({})));
  const snap = obj => ({ docs: Object.entries(obj).map(([id, d]) => ({ id, exists: true, data: () => d })) });
  const mapErr = err => { if (err && err.code === "permission-denied") { const e = new Error(err.message); e.code = "invalid_argument"; return e; } return err; };

  function collection(name){
    const q = {
      w: [],
      limit(n){ q.n = n; return q; },
      where(f, op, v){ q.w.push([f, op, v]); return q; },
      onSnapshot(next, onErr){
        if (name === "events"){
          loadFile("events").then(o => next(snap(o))).catch(e => onErr && onErr(e));
          return () => {};
        }
        if (name === "venues"){
          // static venue data, with edits made by admins (stored in Firestore) layered on top
          let base = null, over = {};
          const emit = () => { if (!base) return; const m = {...base}; for (const [k,v] of Object.entries(over)) m[k] = {...(m[k]||{}), ...v}; next(snap(m)); };
          loadFile("venues").then(o => { base = o; emit(); });
          let unsub = () => {};
          ready.then(() => { if (!fs) return; unsub = fs.collection("venues").onSnapshot(s => { over = {}; s.docs.forEach(d => over[d.id] = d.data()); emit(); }, () => {}); });
          return () => unsub();
        }
        let unsub = () => {};
        ready.then(() => { if (!fs) return onErr && onErr(new Error("no db")); let ref = fs.collection(name); for (const [f,op,v] of q.w) ref = ref.where(f, op, v); unsub = ref.limit(q.n||1000).onSnapshot(next, e => onErr && onErr(mapErr(e))); });
        return () => unsub();
      }
    };
    return q;
  }
  function doc(path){
    return {
      async set(data, opts){ await ready; if (!fs) throw new Error("no db"); try { return await (opts ? fs.doc(path).set(data, opts) : fs.doc(path).set(data)); } catch (e) { throw mapErr(e); } },
      async get(){ await ready; const d = await fs.doc(path).get(); return {exists: d.exists, data: () => d.data()}; }
    };
  }
  // ---- usage stats (shown on admin.html) ----
  // Counters only, no personal data: one doc per day (stats/<date>), per event (evstats/<id>) and per venue (vstats/<id>).
  // Increments are collected and written every few seconds; the Firestore rules allow only small increases.
  const STAT_KEYS = ["views","sessions","visitors","newVisitors","mobile","desktop","ref_direct","ref_search","ref_social","ref_other",
    "tab_date","tab_swipe","tab_top","tab_mine","tab_map","tab_venues","tab_rated","eventOpens","eventLinks","venueOpens","routes"];
  const pend = {day:{}, ev:{}, ve:{}};
  let timer = null, noStats = false;
  try { noStats = localStorage.getItem("noStats") === "1"; } catch {}
  const dayKey = () => { const d = new Date(), p = n => String(n).padStart(2,"0"); return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`; };
  const vid = s => String(s||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,60) || "x";
  async function flush(){
    timer = null;
    if (!fs) return;
    const inc = n => firebase.firestore.FieldValue.increment(n);
    const {day, ev, ve} = pend; pend.day = {}; pend.ev = {}; pend.ve = {};
    try {
      await ready;
      const w = [];
      if (Object.keys(day).length){ const d = {}; for (const [k,n] of Object.entries(day)) d[k] = inc(Math.min(n,20)); w.push(fs.doc("stats/"+dayKey()).set(d, {merge:true})); }
      for (const [id,o] of Object.entries(ev)){ const d = {title:o.title, venue:o.venue, date:o.date}; if (o.opens) d.opens = inc(Math.min(o.opens,20)); if (o.links) d.links = inc(Math.min(o.links,20)); w.push(fs.doc("evstats/"+id).set(d, {merge:true})); }
      for (const [id,o] of Object.entries(ve)) w.push(fs.doc("vstats/"+id).set({name:o.name, opens:inc(Math.min(o.opens,20))}, {merge:true}));
      await Promise.all(w.map(p => p.catch(e => console.warn("stats", e && e.code))));
    } catch {}
  }
  const later = () => { if (!timer) timer = setTimeout(flush, 4000); };
  function count(k){ if (noStats || !STAT_KEYS.includes(k)) return; pend.day[k] = (pend.day[k]||0) + 1; later(); }
  window.track = {
    count,
    event(e, what){ if (noStats || !e || !e.id || e.community || !/^[A-Za-z0-9_-]{1,140}$/.test(e.id)) return;
      const o = pend.ev[e.id] = pend.ev[e.id] || {title:String(e.title||"").slice(0,200), venue:String(e.venue||"").slice(0,80), date:String(e.date||"")};
      o[what] = (o[what]||0) + 1; count(what==="links" ? "eventLinks" : "eventOpens"); },
    venue(name){ if (noStats || !name) return; const id = vid(name); const o = pend.ve[id] = pend.ve[id] || {name:String(name).slice(0,80), opens:0}; o.opens++; count("venueOpens"); }
  };
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden" && timer){ clearTimeout(timer); flush(); } });
  // page view, session, unique visitor per day (browser-local markers, nothing personal is stored)
  if (!noStats) try {
    count("views");
    if (!sessionStorage.getItem("ses")){
      sessionStorage.setItem("ses", "1"); count("sessions");
      count(/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) ? "mobile" : "desktop");
      const r = (() => { try { return new URL(document.referrer).hostname; } catch { return ""; } })();
      if (r !== location.hostname) count(!r ? "ref_direct" : /google|bing|duckduckgo|ecosia|yahoo|qwant|startpage|brave/.test(r) ? "ref_search" : /instagram|facebook|fb\.|t\.co|twitter|x\.com|tiktok|reddit|whatsapp|telegram|linkedin|threads/.test(r) ? "ref_social" : "ref_other");
    }
    const today = dayKey();
    if (localStorage.getItem("seenDay") !== today){ if (!localStorage.getItem("seenDay")) count("newVisitors"); localStorage.setItem("seenDay", today); count("visitors"); }
  } catch {}

  // inc(n): atomic counter increment, used for the shared vote/rating tallies (tallies/<month>)
  // file(name): static JSON baked nightly (e.g. data/community.json), loaded once instead of many Firestore reads
  // batch(ops): several writes that succeed or fail together, ops = [[path, data, opts?], ...]
  // (own votes/ratings and the shared totals: the rules only accept them together, see firestore.rules)
  async function batch(ops){
    await ready; if (!fs) throw new Error("no db");
    const b = fs.batch();
    for (const [path, data, opts] of ops) opts ? b.set(fs.doc(path), data, opts) : b.set(fs.doc(path), data);
    try { return await b.commit(); } catch (e) { throw mapErr(e); }
  }
  const db = { collection, doc, batch, file: name => loadFile(name), inc: n => firebase.firestore.FieldValue.increment(n) };
  const user = {
    async id(){ const u = await ready; return u ? u.uid : null; },
    async canEdit(){ const u = await ready; if (!u || !fs) return false; try { return (await fs.doc("admins/" + u.uid).get()).exists; } catch { return false; } }
  };
  window.claude = { use: async n => n === "db" ? db : n === "user" ? user : null };
})();

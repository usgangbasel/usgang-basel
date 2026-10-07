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
      limit(){ return q; },
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
        ready.then(() => { if (!fs) return onErr && onErr(new Error("no db")); unsub = fs.collection(name).limit(1000).onSnapshot(next, e => onErr && onErr(mapErr(e))); });
        return () => unsub();
      }
    };
    return q;
  }
  function doc(path){
    return {
      async set(data){ await ready; if (!fs) throw new Error("no db"); try { return await fs.doc(path).set(data); } catch (e) { throw mapErr(e); } },
      async get(){ await ready; const d = await fs.doc(path).get(); return {exists: d.exists, data: () => d.data()}; }
    };
  }
  const db = { collection, doc };
  const user = {
    async id(){ const u = await ready; return u ? u.uid : null; },
    async canEdit(){ const u = await ready; if (!u || !fs) return false; try { return (await fs.doc("admins/" + u.uid).get()).exists; } catch { return false; } }
  };
  window.claude = { use: async n => n === "db" ? db : n === "user" ? user : null };
})();

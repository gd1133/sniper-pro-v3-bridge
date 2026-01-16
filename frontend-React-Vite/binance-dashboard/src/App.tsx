import { useState, useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { initializeApp, getApps } from 'firebase/app';
import { getAuth, signInAnonymously, onAuthStateChanged, User, signInWithCustomToken } from 'firebase/auth';
import { getFirestore, collection, onSnapshot, query, addDoc, serverTimestamp, limit } from 'firebase/firestore';
import { 
  TrendingUp, TrendingDown, Target, Wallet, Search, 
  Terminal as TerminalIcon, ShieldCheck, Activity, ChevronRight, 
  Globe, FileText, X, Clock, BarChart3, Zap
} from 'lucide-react';

// --- CONFIGURAÇÃO FIREBASE SEGURA ---
let app: any, auth: any, db: any, appId: string = 'sniper_v3_local';

try {
  // @ts-ignore
  const configStr = typeof __firebase_config !== 'undefined' ? __firebase_config : null;
  const firebaseConfig = configStr ? JSON.parse(configStr) : null;
  
  if (firebaseConfig) {
    app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
    auth = getAuth(app);
    db = getFirestore(app);
    
    // @ts-ignore
    const rawAppId = typeof __app_id !== 'undefined' ? __app_id : 'sniper_v3_local';
    appId = String(rawAppId).replace(/\//g, '_');
  }
} catch (e) {
  console.warn("Firebase não configurado ou erro na inicialização:", e);
}

const SOCKET_SERVER = "http://127.0.0.1:3000";

const App = () => {
  const [data, setData] = useState({ balance: "0.00", pnl: "0.00%", symbol: "SCANNER" });
  const [logs, setLogs] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [showReport, setShowReport] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const terminalRef = useRef<HTMLDivElement>(null);

  // 1. AUTENTICAÇÃO
  useEffect(() => {
    if (!auth) return;
    const initAuth = async () => {
      try {
        // @ts-ignore
        if (typeof __initial_auth_token !== 'undefined' && __initial_auth_token) {
          // @ts-ignore
          await signInWithCustomToken(auth, __initial_auth_token);
        } else {
          await signInAnonymously(auth);
        }
      } catch (err) { console.error("Erro Auth:", err); }
    };
    initAuth();
    const unsubscribe = onAuthStateChanged(auth, (u) => setUser(u));
    return () => unsubscribe();
  }, []);

  // 2. LIGAÇÃO SOCKET
  useEffect(() => {
    const socket: Socket = io(SOCKET_SERVER, { 
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5 
    });

    socket.on('connect', () => setIsConnected(true));
    socket.on('disconnect', () => setIsConnected(false));

    socket.on('update_data', (incoming: any) => {
      if (incoming.market_data) {
        const md = incoming.market_data;
        setData(prev => ({
          ...prev,
          balance: String(md.balance ?? md["SALDO REAL"] ?? prev.balance),
          pnl: String(md.pnl ?? md["PNL SESSÃO"] ?? prev.pnl),
          symbol: String(md.symbol ?? md["ATIVO"] ?? prev.symbol).replace(':USDT', '')
        }));
      }
      if (incoming.log) {
        const newLog = {
          id: Date.now() + Math.random(),
          time: String(incoming.log.time || new Date().toLocaleTimeString()),
          type: String(incoming.log.type || 'INFO').toUpperCase(),
          message: String(incoming.log.message || '')
        };
        setLogs(prev => [newLog, ...prev].slice(0, 30));
      }
    });

    return () => { socket.disconnect(); };
  }, []);

  // 3. BUSCA HISTÓRICO (Firestore)
  useEffect(() => {
    if (!user || !db) return;
    try {
      const tradesRef = collection(db, 'artifacts', appId, 'public', 'data', 'trades');
      const q = query(tradesRef, limit(20));
      return onSnapshot(q, (snapshot) => {
        const trades = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
        setHistory(trades.sort((a:any, b:any) => (b.timestamp?.seconds || 0) - (a.timestamp?.seconds || 0)));
      }, (err) => console.error("Erro Firestore:", err));
    } catch (e) { console.error(e); }
  }, [user]);

  useEffect(() => {
    if (terminalRef.current) terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [logs]);

  // Cálculos de UI seguros
  const pnlValue = parseFloat(data.pnl.replace('%', '')) || 0;
  const isPositive = !data.pnl.includes('-') && pnlValue > 0;
  const isNegative = data.pnl.includes('-');

  return (
    <div className="min-h-screen bg-[#020617] text-slate-200 p-4 md:p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        
        {/* HEADER */}
        <header className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
          <div className="flex items-center gap-4">
            <div className="bg-blue-600 p-3 rounded-2xl shadow-lg shadow-blue-500/20"><Target size={28} /></div>
            <div>
              <h1 className="text-2xl font-black tracking-tighter italic uppercase leading-none">Sniper<span className="text-blue-500">Alpha</span> V3</h1>
              <p className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">2 Slots • High Frequency</p>
            </div>
          </div>
          <div className="flex gap-3">
             <button onClick={() => setShowReport(true)} className="bg-slate-900/80 px-4 py-2 rounded-xl border border-white/5 text-[10px] font-bold uppercase tracking-widest text-blue-400 hover:bg-slate-800 transition-all flex items-center gap-2">
               <FileText size={14}/> Relatório
             </button>
             <div className={`px-4 py-2 rounded-xl border flex items-center gap-2 ${isConnected ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-red-500/5 border-red-500/20'}`}>
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></div>
                <span className="text-[10px] font-bold uppercase tracking-widest">{isConnected ? 'ON' : 'OFF'}</span>
             </div>
          </div>
        </header>

        {/* CARDS */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-slate-900/40 backdrop-blur-md border border-white/5 p-8 rounded-[2.5rem]">
            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Saldo Disponível</p>
            <h2 className="text-4xl font-black text-white tracking-tighter">${parseFloat(data.balance).toFixed(2)}</h2>
          </div>

          <div className="bg-slate-900/40 backdrop-blur-md border border-white/5 p-8 rounded-[2.5rem]">
            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">PNL da Sessão</p>
            <h2 className={`text-4xl font-black tracking-tighter ${isPositive ? 'text-emerald-500' : isNegative ? 'text-red-500' : 'text-white'}`}>
              {data.pnl}
            </h2>
          </div>

          <div className="bg-slate-900/40 backdrop-blur-md border border-white/5 p-8 rounded-[2.5rem] border-b-4 border-blue-600">
            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Ativo Atual</p>
            <h2 className="text-2xl font-black text-blue-500 truncate uppercase">{data.symbol}</h2>
          </div>
        </div>

        {/* TERMINAL */}
        <div className="bg-slate-900/40 border border-white/5 rounded-[2.5rem] overflow-hidden flex flex-col h-[400px]">
          <div className="bg-white/[0.02] px-6 py-4 border-b border-white/5 flex items-center gap-2">
            <TerminalIcon size={14} className="text-slate-500" />
            <span className="text-[10px] font-black uppercase text-slate-400">Live Telemetry</span>
          </div>
          <div ref={terminalRef} className="flex-1 overflow-y-auto p-6 font-mono text-[11px] space-y-2 scrollbar-hide">
            {logs.length === 0 ? <div className="text-slate-700 italic">{" >> "} Aguardando motor Python...</div> : 
              logs.map(log => (
                <div key={log.id} className="flex items-start gap-3">
                  <span className="text-slate-600 shrink-0 font-bold">[{log.time}]</span>
                  <span className={`font-black uppercase shrink-0 ${log.type === 'SUCCESS' ? 'text-emerald-500' : log.type === 'ERROR' ? 'text-red-500' : 'text-blue-500'}`}>{log.type}</span>
                  <span className="text-slate-400">{log.message}</span>
                </div>
              ))
            }
          </div>
        </div>

        {/* MODAL RELATÓRIO */}
        {showReport && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-sm">
            <div className="bg-[#0f172a] border border-white/10 w-full max-w-lg rounded-[2.5rem] overflow-hidden shadow-2xl">
              <div className="p-6 border-b border-white/5 flex justify-between items-center">
                <h3 className="text-sm font-black uppercase tracking-widest">Histórico de Lucros</h3>
                <button onClick={() => setShowReport(false)} className="text-slate-500 hover:text-white"><X size={20} /></button>
              </div>
              <div className="p-6 h-[300px] overflow-y-auto space-y-3">
                {history.length === 0 ? <p className="text-center text-slate-600 text-xs py-10 uppercase font-bold">Sem dados no Firestore</p> : 
                  history.map((item: any) => (
                    <div key={item.id} className="bg-slate-900 p-4 rounded-2xl border border-white/5 flex items-center gap-4">
                      <BarChart3 className="text-blue-500" size={16}/>
                      <div className="text-[10px]">
                        <p className="text-slate-500 font-bold uppercase mb-0.5">{item.time}</p>
                        <p className="font-bold text-slate-200">{item.message}</p>
                      </div>
                    </div>
                  ))
                }
              </div>
            </div>
          </div>
        )}
      </div>
      <style>{`.scrollbar-hide::-webkit-scrollbar { display: none; }`}</style>
    </div>
  );
};

export default App;
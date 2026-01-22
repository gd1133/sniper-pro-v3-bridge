import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import { 
  Zap, 
  Activity, 
  TrendingUp, 
  TrendingDown, 
  Wallet, 
  ShieldCheck, 
  Volume2, 
  History, 
  MessageSquare,
  RefreshCw,
  Target
} from 'lucide-react';

/**
 * CONFIGURAÇÃO DE REDE
 * Liga à ponte Node.js (server.js) na porta 3000.
 */
const socket = io('http://localhost:3000', {
  reconnection: true,
  reconnectionAttempts: 20,
  reconnectionDelay: 1000
});

const GEMINI_KEY = ""; // Chave injetada pelo ambiente para Voz IA

const App = () => {
  // --- ESTADOS DO SISTEMA ---
  const [activeTrade, setActiveTrade] = useState(null);
  const [logs, setLogs] = useState([]);
  const [balance, setBalance] = useState(0);
  const [equity, setEquity] = useState(0);
  const [status, setStatus] = useState('offline');
  const [isSpeaking, setIsSpeaking] = useState(false);

  // --- ESCUTA DE DADOS EM TEMPO REAL ---
  useEffect(() => {
    socket.on('connect', () => {
      setStatus('online');
      console.log("✅ Conexão Dashboard/Ponte estabelecida.");
    });

    socket.on('disconnect', () => setStatus('offline'));

    socket.on('update', (data) => {
      if (!data) return;
      console.log("📡 Sinal recebido:", data);
      
      // Processamento de Dados de Mercado
      if (data.market_data) {
        const md = data.market_data;
        setActiveTrade(md);
        
        // Atualização Segura de Saldo e Equity (Banca em Risco)
        const baseBalance = parseFloat(md.balance) || balance || 0;
        setBalance(baseBalance);
        
        if (md.pnl && typeof md.pnl === 'string') {
          // Limpa caracteres especiais para calcular
          const pnlNum = parseFloat(md.pnl.replace(/[+%]/g, '')) || 0;
          const invested = baseBalance * 0.30; // 30% conforme estratégia agressiva
          const currentPnlCash = invested * (pnlNum / 100);
          setEquity(baseBalance + currentPnlCash);
        } else {
          setEquity(baseBalance);
        }
      }

      // Processamento de Logs
      if (data.log && data.log.message) {
        setLogs(prev => [data.log, ...prev].slice(0, 50));
        
        // Aciona Voz IA se o log for do tipo áudio
        if (data.log.type === 'ai_voice') {
          handleVoiceAI(data.log.message);
        }
      }
    });

    return () => socket.off('update');
  }, [balance]);

  // --- MOTOR DE VOZ (Gemini TTS) ---
  const handleVoiceAI = async (text) => {
    if (isSpeaking || !text || !GEMINI_KEY) return;
    setIsSpeaking(true);
    try {
      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=${GEMINI_KEY}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: `Say this naturally and fast: ${text}` }] }],
          generationConfig: {
            responseModalities: ["AUDIO"],
            speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: "Puck" } } }
          }
        })
      });
      const result = await response.json();
      const audioBase64 = result.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
      
      if (audioBase64) {
        const binary = atob(audioBase64);
        const array = new Int16Array(binary.length / 2);
        for (let i = 0; i < binary.length; i += 2) array[i / 2] = (binary.charCodeAt(i + 1) << 8) | binary.charCodeAt(i);
        const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
        const buffer = ctx.createBuffer(1, array.length, 24000);
        buffer.getChannelData(0).set(Array.from(array).map(v => v / 32768));
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(ctx.destination);
        source.start();
      }
    } catch (e) { console.error("Erro Áudio:", e); }
    finally { setTimeout(() => setIsSpeaking(false), 8000); }
  };

  // --- UTILITÁRIO: LIMPEZA DE SÍMBOLO ---
  const formatSymbol = (sym) => {
    if (!sym) return "---";
    return sym.split('/')[0].split(':')[0]; // Transforma AIA/USDT:USDT em AIA
  };

  return (
    <div className="min-h-screen bg-[#08090a] text-slate-300 font-sans p-4 md:p-8">
      
      {/* HEADER DE COMANDO */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center mb-10 border-b border-white/5 pb-8 gap-6">
        <div className="flex items-center gap-5">
          <div className="bg-zinc-900 p-4 rounded-2xl border border-white/10 shadow-[0_0_20px_rgba(243,186,47,0.1)]">
            <Zap className="text-yellow-500 fill-yellow-500" size={28} />
          </div>
          <div>
            <h1 className="text-4xl font-black italic tracking-tighter text-white">SNIPER MASTER V3</h1>
            <div className="flex items-center gap-2 mt-1">
              <div className={`w-2 h-2 rounded-full ${status === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></div>
              <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                Ponte Status: {status} | Monitor 5s Ativo
              </p>
            </div>
          </div>
        </div>

        <div className="bg-zinc-900/80 px-8 py-4 rounded-[2rem] border border-white/5 shadow-xl text-right">
          <p className="text-[9px] font-black text-slate-500 uppercase tracking-tighter mb-1">Banca em Risco (Equity)</p>
          <p className="text-3xl font-mono font-black text-emerald-400">
            ${equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
      </header>

      {/* GRID DE OPERAÇÃO */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LADO ESQUERDO: TRADE ATIVO */}
        <div className="lg:col-span-8 space-y-6">
          <div className="bg-zinc-900 rounded-[3rem] p-10 border border-white/5 relative overflow-hidden shadow-2xl min-h-[500px] flex flex-col">
            
            <div className="flex justify-between items-center mb-12">
              <span className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">
                <Target size={14} className="text-yellow-500" /> Patrulha em Tempo Real
              </span>
              <div className={`flex items-center gap-3 px-4 py-2 rounded-full border ${isSpeaking ? 'bg-yellow-500/10 border-yellow-500 text-yellow-500' : 'bg-black/20 border-white/5 text-slate-500'}`}>
                <Volume2 size={16} className={isSpeaking ? 'animate-bounce' : ''} />
                <span className="text-[10px] font-black uppercase tracking-widest">
                  {isSpeaking ? 'IA Falando' : 'IA em Escuta'}
                </span>
              </div>
            </div>

            {activeTrade && activeTrade.symbol ? (
              <div className="flex-1 flex flex-col justify-between animate-in fade-in duration-500">
                <div className="flex justify-between items-end">
                  <div>
                    <h2 className="text-8xl font-black text-white tracking-tighter">{formatSymbol(activeTrade.symbol)}</h2>
                    <div className="flex items-center gap-3 mt-4">
                      <span className={`px-4 py-1 rounded-full text-[10px] font-black uppercase border ${activeTrade.pnl?.includes('-') ? 'bg-rose-500/10 border-rose-500/30 text-rose-500' : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500'}`}>
                        {activeTrade.pnl?.includes('-') ? 'Short Mode' : 'Long Mode'}
                      </span>
                      <span className="text-xl font-mono text-slate-400">${activeTrade.price || '0.00'}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] font-black text-slate-600 uppercase mb-2">PNL da Onda</p>
                    <p className={`text-8xl font-black tracking-tighter leading-none ${activeTrade.pnl?.includes('-') ? 'text-rose-500' : 'text-emerald-500'}`}>
                      {activeTrade.pnl || '0.00%'}
                    </p>
                  </div>
                </div>

                <div className="mt-12 bg-black/40 p-8 rounded-[2rem] border border-white/5">
                  <p className="text-xl font-medium text-slate-200 italic leading-relaxed">
                    "{activeTrade.analysis || 'O Agente Gemini está a analisar o fluxo do mercado...'}"
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center space-y-8 opacity-40">
                <RefreshCw size={80} className="text-slate-800 animate-spin" />
                <div className="text-center">
                  <h3 className="text-2xl font-black uppercase tracking-[0.2em] text-white">Scanner Master V3 Ativo</h3>
                  <p className="text-xs font-bold text-slate-600 uppercase mt-2">Aguardando vela de explosão ou derretimento...</p>
                </div>
              </div>
            )}
          </div>

          {/* WIDGETS DE STATUS */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-zinc-900/50 p-6 rounded-3xl border border-white/5 flex items-center gap-4">
              <div className="bg-blue-500/10 p-3 rounded-2xl"><TrendingUp className="text-blue-500" /></div>
              <div><p className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Tendência</p><p className="text-lg font-bold">ALTA FORÇA</p></div>
            </div>
            <div className="bg-zinc-900/50 p-6 rounded-3xl border border-white/5 flex items-center gap-4">
              <div className="bg-emerald-500/10 p-3 rounded-2xl"><ShieldCheck className="text-emerald-500" /></div>
              <div><p className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Status</p><p className="text-lg font-bold text-emerald-500">PROTEGIDO</p></div>
            </div>
            <div className="bg-zinc-900/50 p-6 rounded-3xl border border-white/5 flex items-center gap-4">
              <div className="bg-yellow-500/10 p-3 rounded-2xl"><Wallet className="text-yellow-500" /></div>
              <div><p className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Saldo Real</p><p className="text-lg font-bold">${balance.toFixed(2)}</p></div>
            </div>
          </div>
        </div>

        {/* LADO DIREITO: LOGS MATRIX */}
        <div className="lg:col-span-4 bg-[#0c0d0e] rounded-[3rem] border border-white/5 p-8 flex flex-col h-[700px] shadow-2xl relative overflow-hidden">
          <div className="flex justify-between items-center mb-8">
            <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
              <History size={14} className="text-yellow-500" /> Logs de Segurança
            </h3>
            <span className="text-[8px] font-black bg-emerald-500/10 text-emerald-500 px-2 py-1 rounded-md border border-emerald-500/20 uppercase tracking-widest">Live</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
            {logs.length > 0 ? logs.map((log, i) => (
              <div key={i} className={`p-5 rounded-2xl border-l-4 transition-all duration-300 hover:bg-white/5 ${
                log.type === 'ai_voice' ? 'bg-yellow-500/5 border-yellow-500' : 
                log.type === 'success' ? 'bg-emerald-500/5 border-emerald-500' : 'bg-white/5 border-zinc-800'
              }`}>
                <div className="flex justify-between mb-2 opacity-30 text-[9px] font-bold">
                  <span className="uppercase tracking-widest">{log.type === 'ai_voice' ? 'Agente Voz' : 'Sistema Core'}</span>
                  <span className="font-mono">{log.time}</span>
                </div>
                <p className={`text-[11px] leading-relaxed ${log.type === 'ai_voice' ? 'text-yellow-100 font-bold' : 'text-slate-400'}`}>
                  {log.message}
                </p>
              </div>
            )) : (
              <div className="h-full flex flex-col items-center justify-center opacity-5">
                <MessageSquare size={48} />
                <p className="text-[10px] font-black uppercase mt-4 tracking-widest">Sem Sinais</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ESTILOS CUSTOMIZADOS */}
      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.05); border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        @keyframes fade-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-in { animation: fade-in 0.5s ease-out forwards; }
      `}</style>
    </div>
  );
};

export default App;
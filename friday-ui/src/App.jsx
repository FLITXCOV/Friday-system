import React, { useState, useEffect } from 'react';
import {
  LiveKitRoom,
  RoomAudioRenderer,
  BarVisualizer,
  useVoiceAssistant
} from '@livekit/components-react';
import './App.css';

/* ---------------------------------------------------------------------------
   App — Token Fetch + LiveKit Connection
   --------------------------------------------------------------------------- */
function App() {
  const [token, setToken] = useState(null);
  const [url, setUrl] = useState(null);
  const [connecting, setConnecting] = useState(true);

  useEffect(() => {
    fetch('http://127.0.0.1:8001/api/token')
      .then(res => res.json())
      .then(data => { setToken(data.token); setUrl(data.url); setConnecting(false); })
      .catch(() => setConnecting(false));
  }, []);

  if (connecting) {
    return (
      <div className="boot-screen">
        <div className="boot-text">ESTABLISHING UPLINK</div>
        <div className="boot-bar"><div className="boot-bar-inner" /></div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="boot-screen error">
        <div className="boot-text">CORE SYSTEMS OFFLINE</div>
      </div>
    );
  }

  return (
    <LiveKitRoom serverUrl={url} token={token} connect={true} audio={true} className="lk-room">
      <RoomAudioRenderer />
      <FridayHUD />
    </LiveKitRoom>
  );
}

/* ---------------------------------------------------------------------------
   F.R.I.D.A.Y. HUD — Ultra Premium Arc Reactor Interface
   --------------------------------------------------------------------------- */
function FridayHUD() {
  const { state, audioTrack } = useVoiceAssistant();
  const s = state || 'idle';

  const labels = { idle: 'STANDBY', listening: 'LISTENING', speaking: 'SPEAKING', thinking: 'PROCESSING' };

  /* 25 particles — mixed sizes */
  const particles = [];
  const sizes = ['sm','sm','md','sm','lg','sm','md','sm','sm','lg','sm','sm','md','sm','sm','sm','lg','md','sm','sm','sm','md','sm','lg','sm'];
  for (let i = 0; i < 25; i++) particles.push(<div key={`p${i}`} className={`p ${sizes[i]}`} />);

  /* 16 light rays */
  const rays = Array.from({ length: 16 }, (_, i) => <div key={`r${i}`} className="ray" />);

  return (
    <div className={`friday-app ${s}`}>

      {/* ---- Deep space background ---- */}
      <div className="nebula">
        <div className="nebula-cloud c1" />
        <div className="nebula-cloud c2" />
        <div className="nebula-cloud c3" />
      </div>
      <div className="hex-grid" />
      <div className="scan-beam" />
      <div className="particles-layer">{particles}</div>

      {/* ---- HUD frame ---- */}
      <div className="hud-frame">
        <div className="corner tl" />
        <div className="corner tr" />
        <div className="corner bl" />
        <div className="corner br" />
        <div className="edge-line top" />
        <div className="edge-line bottom" />
      </div>

      {/* ---- Main UI ---- */}
      <div className="ui-layer">

        {/* Header */}
        <div className="hdr">
          <div className="brand">
            <h1 className="brand-name">F.R.I.D.A.Y.</h1>
            <div className="brand-sub">Female Replacement Intelligent Digital Assistant Youth</div>
            <div className="brand-line" />
          </div>
          <div className="status">
            <span className={`indicator ${s}`} />
            {labels[s] || 'STANDBY'}
          </div>
        </div>

        {/* Arc Reactor — centerpiece */}
        <div className="reactor-zone">

          {/* Left glass panel */}
          <div className="panel left">
            <div className="d-row">
              <span className="d-label">SYS</span>
              <div className="d-bar"><div className="d-fill" style={{ width: '68%' }} /></div>
            </div>
            <div className="d-row">
              <span className="d-label">CPU</span>
              <div className="d-bar"><div className="d-fill" style={{ width: '45%' }} /></div>
            </div>
            <div className="d-row">
              <span className="d-label">MEM</span>
              <div className="d-bar"><div className="d-fill" style={{ width: '31%' }} /></div>
            </div>
            <div className="d-row">
              <span className="d-label">NET</span>
              <span className="d-val">SECURE</span>
            </div>
            <div className="d-row">
              <span className="d-label">LAT</span>
              <span className="d-val">23ms</span>
            </div>
          </div>

          {/* The Reactor */}
          <div className="reactor">
            <div className="reactor-halo" />
            <div className="r r5" />
            <div className="r r4" />
            <div className="r r3" />
            <div className="r r2" />
            <div className="r r1" />
            <div className="rays">{rays}</div>
            <div className="core" />
            <div className="wave" />
            <div className="wave" />
            <div className="wave" />

            {(s === 'speaking' || s === 'listening') && (
              <div className="viz-wrap">
                <BarVisualizer
                  state={state}
                  trackRef={audioTrack}
                  barCount={7}
                  options={{ minHeight: 8, maxHeight: 140 }}
                  className="friday-bars"
                />
              </div>
            )}
          </div>

          {/* Right glass panel */}
          <div className="panel right">
            <div className="d-row">
              <span className="d-label">STATUS</span>
              <span className="d-val">ONLINE</span>
            </div>
            <div className="d-row">
              <span className="d-label">TEMP</span>
              <span className="d-val">42°C</span>
            </div>
            <div className="d-row">
              <span className="d-label">LLM</span>
              <span className="d-val">GEMMA</span>
            </div>
            <div className="d-row">
              <span className="d-label">STT</span>
              <span className="d-val">SARVAM</span>
            </div>
            <div className="d-row">
              <span className="d-label">TTS</span>
              <span className="d-val">XI-LABS</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="ftr">
          <div className="ftr-col">
            <span className="ftr-text">Stark Industries — AI Division</span>
            <div className="ftr-accent" />
          </div>
          <div className="ftr-col right">
            <span className="ftr-text">Neural Core v2.0 — Active</span>
            <div className="ftr-accent" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

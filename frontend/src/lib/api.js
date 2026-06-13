import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL;
export const API = `${BASE}/api`;

// Anonymous demo-session isolation (CP-07): stable per-browser UUID.
function getSessionId() {
  let sid = localStorage.getItem("pulse_demo_session");
  if (!sid) {
    sid = (crypto.randomUUID && crypto.randomUUID()) ||
      `sess-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem("pulse_demo_session", sid);
  }
  return sid;
}
export const SESSION_ID = getSessionId();

const client = axios.create({ baseURL: API, timeout: 60000 });
client.interceptors.request.use((cfg) => {
  cfg.headers["X-Demo-Session-ID"] = getSessionId();
  return cfg;
});

// Vercel SPA mode serves index.html (HTTP 200) for unknown/unreachable backend
// paths. Detect that string body and reject so pages show an error state instead
// of crashing while trying to read HTML as JSON.
client.interceptors.response.use(
  (response) => {
    if (typeof response.data === "string") {
      return Promise.reject(new Error("Backend not reachable"));
    }
    return response;
  },
  (error) => Promise.reject(error)
);

export const getMeta = () => client.get("/meta").then((r) => r.data);
export const getCockpit = (region) => client.get("/cockpit", { params: { region } }).then((r) => r.data);
export const getOpportunity = (region) => client.get("/opportunity", { params: { region } }).then((r) => r.data);
export const postBrief = (body) => client.post("/brief", body).then((r) => r.data);
export const getModelBudget = () => client.get("/model-budget").then((r) => r.data);
export const getLeakages = (region) => client.get("/leakages", { params: { region } }).then((r) => r.data);
export const getLeakage = (id) => client.get(`/leakages/${id}`).then((r) => r.data);
export const getJourneys = (params) => client.get("/journeys", { params }).then((r) => r.data);
export const getJourney = (id) => client.get(`/journeys/${id}`).then((r) => r.data);
export const postSimulation = (body) => client.post("/simulation", body).then((r) => r.data);
export const getDataQuality = (region) => client.get("/data-quality", { params: { region } }).then((r) => r.data);
export const getEvaluation = () => client.get("/evaluation").then((r) => r.data);
export const getInterventions = () => client.get("/interventions").then((r) => r.data);
export const createIntervention = (body) => client.post("/interventions", body).then((r) => r.data);
export const updateIntervention = (id, body) => client.patch(`/interventions/${id}`, body).then((r) => r.data);
export const claimProof = (id, body) => client.post(`/interventions/${id}/proof`, body).then((r) => r.data);
export const verifyClosure = (id, body) => client.post(`/interventions/${id}/verify`, body).then((r) => r.data);
export const resetSession = () => client.post("/session/reset").then((r) => r.data);

export default client;

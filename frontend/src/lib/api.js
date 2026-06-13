import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL;
export const API = `${BASE}/api`;

const client = axios.create({ baseURL: API, timeout: 60000 });

export const getMeta = () => client.get("/meta").then((r) => r.data);
export const getCockpit = (region) => client.get("/cockpit", { params: { region } }).then((r) => r.data);
export const postBrief = (body) => client.post("/brief", body).then((r) => r.data);
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

export default client;

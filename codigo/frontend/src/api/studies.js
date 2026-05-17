import api from "./client"

// Estudios
export const getStudies  = (params) => api.get("/api/studies", { params }).then((r) => r.data)
export const getStudy    = (id)     => api.get(`/api/studies/${id}`).then((r) => r.data)
export const createStudy = (data)   => api.post("/api/studies", data).then((r) => r.data)
export const updateStudy = (id, data) => api.put(`/api/studies/${id}`, data).then((r) => r.data)
export const deleteStudy = (id)     => api.delete(`/api/studies/${id}`)
export const transitionState = (id, estado, error_msg) =>
  api.post(`/api/studies/${id}/transition`, { estado, error_msg }).then((r) => r.data)

// Corpus
export const getCorpus      = (id)       => api.get(`/api/studies/${id}/corpus`).then((r) => r.data)
export const deleteCorpusFile = (id, fid) => api.delete(`/api/studies/${id}/corpus/${fid}`)

// Drive
export const getDriveStatus  = ()   => api.get("/api/drive/status").then((r) => r.data)
export const getDriveAuthUrl = ()   => api.get("/api/drive/auth-url").then((r) => r.data)
export const syncStudy       = (id) => api.post(`/api/drive/sync/${id}`).then((r) => r.data)

// Procesamiento documental
export const processCorpus   = (id, reprocess = false) =>
  api.post(`/api/studies/${id}/documents/process`, null, { params: { reprocess } }).then((r) => r.data)
export const getExtractionSummary = (id) =>
  api.get(`/api/studies/${id}/documents/extractions/summary`).then((r) => r.data)

// GIS
export const analyzeGIS    = (id) => api.post(`/api/studies/${id}/gis/analyze`).then((r) => r.data)
export const getGISResults = (id) => api.get(`/api/studies/${id}/gis`).then((r) => r.data)
export const getStudyGeoJSON = (id) => api.get(`/api/studies/${id}/gis/geojson`).then((r) => r.data)

// Informes
export const getReports      = (id)        => api.get(`/api/studies/${id}/reports`).then((r) => r.data)
export const generateReport  = (id)        => api.post(`/api/studies/${id}/reports`).then((r) => r.data)
export const approveReport   = (id, rid)   => api.post(`/api/studies/${id}/reports/${rid}/approve`).then((r) => r.data)
export const downloadReportUrl = (id, rid) => `${api.defaults.baseURL}/api/studies/${id}/reports/${rid}/download`

// Mapa
export const getResguardosGeoJSON = (params) => api.get("/api/map/resguardos", { params }).then((r) => r.data)
export const getMapLeyenda        = ()        => api.get("/api/map/leyenda").then((r) => r.data)

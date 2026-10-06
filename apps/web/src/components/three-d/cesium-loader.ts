type CesiumModule = typeof import("cesium");
declare global {
  interface Window {
    Cesium?: CesiumModule;
    CESIUM_BASE_URL?: string;
  }
}
let loading: Promise<CesiumModule> | undefined;
export function loadCesium(): Promise<CesiumModule> {
  if (window.Cesium) return Promise.resolve(window.Cesium);
  if (loading) return loading;
  window.CESIUM_BASE_URL = "/cesium/";
  loading = new Promise<CesiumModule>((resolve, reject) => {
    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = "/cesium/Widgets/widgets.css";
    document.head.append(css);
    const script = document.createElement("script");
    script.src = "/cesium/Cesium.js";
    script.async = true;
    const timer = window.setTimeout(() => {
      script.remove();
      reject(new Error("Cesium load timed out"));
    }, 20000);
    script.onload = () => {
      clearTimeout(timer);
      if (window.Cesium) resolve(window.Cesium);
      else reject(new Error("Cesium unavailable"));
    };
    script.onerror = () => {
      clearTimeout(timer);
      script.remove();
      reject(new Error("Cesium unavailable"));
    };
    document.head.append(script);
  }).catch((error) => {
    loading = undefined;
    throw error;
  });
  return loading;
}

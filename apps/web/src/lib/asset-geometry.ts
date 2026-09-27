import type { GeoJsonGeometry, Position } from "@/types/asset";
export function geometryPositions(geometry: GeoJsonGeometry): Position[] {
  switch (geometry.type) {
    case "Point":
      return [geometry.coordinates];
    case "LineString":
      return geometry.coordinates;
    case "Polygon":
      return geometry.coordinates.flat();
  }
}

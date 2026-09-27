export type Reservoir = {
  id: string;
  code: string;
  name: string;
  province: string | null;

  data_status: string;
  mvdt_level: number;

  description: string | null;

  longitude: number;
  latitude: number;
};

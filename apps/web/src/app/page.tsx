import { getReservoirs } from "@/lib/api";


export const dynamic = "force-dynamic";

export default async function HomePage() {
  const reservoirs = await getReservoirs();

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-3xl font-semibold">
          Irrigation MVDT Platform
        </h1>

        <p className="mt-2 text-slate-600">
          Reservoir registry loaded from FastAPI + PostGIS. Development seed data only; not verified research data.
        </p>

        <div className="mt-8 grid gap-4">
          {reservoirs.map((reservoir) => (
            <article
              key={reservoir.id}
              className="rounded-xl border bg-white p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-medium">
                    {reservoir.name}
                  </h2>

                  <p className="text-sm text-slate-500">
                    {reservoir.code}
                  </p>
                </div>

                <span className="rounded-full bg-slate-100 px-3 py-1 text-sm">
                  Level {reservoir.mvdt_level}
                </span>
              </div>

              <dl className="mt-4 grid gap-2 text-sm">
                <div>
                  <dt className="font-medium">
                    Province
                  </dt>
                  <dd>
                    {reservoir.province ?? "Unknown"}
                  </dd>
                </div>

                <div>
                  <dt className="font-medium">
                    Data Status
                  </dt>
                  <dd>
                    {reservoir.data_status}
                  </dd>
                </div>

                <div>
                  <dt className="font-medium">
                    Coordinates
                  </dt>
                  <dd>
                    {reservoir.latitude}, {reservoir.longitude}
                  </dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}

import { useState } from "react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file) return;

    setLoading(true);
    setResult(null);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${BACKEND_URL}/dev/parse`, {
        method: "POST",
        body: formData,
      });
      const body = await response.json();

      if (response.ok) {
        setResult(body);
      } else {
        setError({ tipo: body.error ?? "Erro desconhecido", mensagem: body.message ?? "" });
      }
    } catch (err) {
      setError({
        tipo: "Falha de rede",
        mensagem: `Não foi possível chamar ${BACKEND_URL}/dev/parse — o backend está rodando? (${err.message})`,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 800, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>InBody370S — harness de teste (descartável)</h1>
      <p style={{ color: "#a00" }}>
        ⚠️ Ferramenta de desenvolvimento temporária, sem autenticação e sem persistência.
        Ver <code>docs/specs/harness-teste-parser.md</code>.
      </p>

      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files[0] ?? null)}
        />
        <button type="submit" disabled={!file || loading} style={{ marginLeft: "1rem" }}>
          {loading ? "Extraindo..." : "Extrair dados"}
        </button>
      </form>

      {error && (
        <div style={{ marginTop: "1.5rem", padding: "1rem", background: "#fee", border: "1px solid #c00" }}>
          <strong>Erro ({error.tipo})</strong>
          <p>{error.mensagem}</p>
        </div>
      )}

      {result && (
        <div style={{ marginTop: "1.5rem" }}>
          <h2>Avaliação</h2>
          <table border="1" cellPadding="6" style={{ borderCollapse: "collapse" }}>
            <tbody>
              <tr>
                <td>Aparelho</td>
                <td>{result.evaluation.device_model}</td>
              </tr>
              <tr>
                <td>Data/Hora</td>
                <td>{result.evaluation.measured_at}</td>
              </tr>
              <tr>
                <td>ID do paciente</td>
                <td>{result.evaluation.patient_ref.device_id}</td>
              </tr>
              <tr>
                <td>Biometria</td>
                <td>
                  {result.evaluation.biometrics.altura_cm} cm,{" "}
                  {result.evaluation.biometrics.idade} anos,{" "}
                  {result.evaluation.biometrics.sexo}
                </td>
              </tr>
            </tbody>
          </table>

          <h2 style={{ marginTop: "1.5rem" }}>Métricas</h2>
          <table border="1" cellPadding="6" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th>key</th>
                <th>value</th>
                <th>unit</th>
                <th>ref_min</th>
                <th>ref_max</th>
              </tr>
            </thead>
            <tbody>
              {result.metrics.map((m) => (
                <tr key={m.key}>
                  <td>{m.key}</td>
                  <td>{m.value}</td>
                  <td>{m.unit ?? "—"}</td>
                  <td>{m.ref_min ?? "—"}</td>
                  <td>{m.ref_max ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <p style={{ marginTop: "1rem" }}>
            <strong>confidence:</strong> {result.raw_extraction.confidence}
            {result.raw_extraction.warnings.length > 0 && (
              <ul>
                {result.raw_extraction.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
          </p>
        </div>
      )}
    </div>
  );
}

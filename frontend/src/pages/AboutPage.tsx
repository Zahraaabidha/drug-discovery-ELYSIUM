import React from "react";

const models = [
  {
    name: "RDKit",
    role: "Descriptor calculation, Lipinski and ADMET heuristics, and molecule rendering for quick visual QA.",
  },
  {
    name: "DeepPurpose",
    role: "Drug–target interaction scoring using BindingDB pretrained checkpoints; fallback stubs keep pipelines testable.",
  },
  {
    name: "ChemBERTa",
    role: "Semantic similarity between generated scaffolds and known compounds to contextualize novelty claims.",
  },
];

const disclaimers = [
  "ELYSIUM is a research prototype; no clinical or therapeutic claims are made.",
  "Generated scores are model-dependent and require medicinal chemistry review before experimental action.",
  "Knowledge graph data may be incomplete and serves exploratory analysis only.",
];

const AboutPage: React.FC = () => {
  return (
    <div className="max-w-5xl mx-auto px-6 py-12 space-y-12">
      <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-8">
        <p className="text-sm uppercase tracking-[0.3em] text-slate-400">System overview</p>
        <h2 className="text-3xl font-serif text-slate-900 mt-3">Agent-assisted methodology</h2>
        <p className="text-slate-600 mt-4">
          The ELYSIUM stack blends deterministic planners with chemistry models so every discovery run is traceable. FastAPI
          coordinates generation, scoring, and graph persistence. SQLite anchors experiment metadata, while ArangoDB captures
          molecular relationships for downstream reasoning.
        </p>
      </section>

      <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-8">
        <h3 className="text-2xl font-serif text-slate-900">Discovery pipeline</h3>
        <ol className="mt-4 space-y-3 text-sm text-slate-700 list-decimal list-inside">
          <li>Define biological target, molecule count, and medicinal filters.</li>
          <li>Sample candidate scaffolds from curated libraries (future: transformer generators).</li>
          <li>Score against target sequences via DeepPurpose (fallback stub ensures determinism).</li>
          <li>Annotate with RDKit ADMET metrics and similarity to known drugs.</li>
          <li>Persist to structured runs and attach nodes/edges inside the knowledge graph.</li>
        </ol>
      </section>

      <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-8">
        <h3 className="text-2xl font-serif text-slate-900">Model inventory</h3>
        <div className="mt-6 grid gap-6 md:grid-cols-3">
          {models.map((model) => (
            <div key={model.name} className="border border-slate-200 rounded-xl p-4 bg-slate-50">
              <h4 className="text-lg font-semibold text-slate-900">{model.name}</h4>
              <p className="text-sm text-slate-600 mt-2">{model.role}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-8">
        <h3 className="text-2xl font-serif text-slate-900">Limitations & academic honesty</h3>
        <ul className="mt-4 space-y-3 text-sm text-slate-700">
          {disclaimers.map((note) => (
            <li key={note} className="flex gap-3">
              <span className="mt-1 h-2 w-2 rounded-full bg-amber-500" />
              <p>{note}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
};

export default AboutPage;

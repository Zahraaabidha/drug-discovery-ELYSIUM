import React from "react";

interface MoleculeResultRowProps {
  smiles: string;
  score: number;
  imageUrl: string;
  similarDrug?: {
    name: string;
    similarity?: number;
  };
  admet?: {
    molecular_weight: number;
    logp: number;
    hbd: number;
    hba: number;
    tpsa: number;
    lipinski_pass: boolean;
  };
  explanation?: string;
  variant?: "primary" | "secondary";
}

const MoleculeResultRow: React.FC<MoleculeResultRowProps> = ({
  smiles,
  score,
  imageUrl,
  similarDrug,
  admet,
  explanation,
  variant = "primary",
}) => {
  const scoreColor = score >= 0.8 ? "text-green-600" : "text-slate-700";
  const cardAccent =
    variant === "primary"
      ? "border-blue-100 ring-1 ring-blue-50"
      : "border-slate-200";

  return (
    <article className={`bg-white ${cardAccent} rounded-2xl p-5 shadow-sm space-y-4`}>
      <div className="flex items-start justify-between gap-3">
        <p className="font-mono text-sm text-slate-600 break-all max-w-xl">
          {smiles}
        </p>
        <div className={`text-sm font-semibold ${scoreColor}`}>
          Score {score.toFixed(3)}
        </div>
      </div>

      <div className="flex flex-col gap-4 md:flex-row">
        <img
          src={imageUrl}
          alt={smiles}
          className="w-36 h-36 rounded-xl border border-slate-100 bg-slate-50 object-contain"
        />

        <div className="flex-1 space-y-3 text-sm text-slate-700">
          {similarDrug && (
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="text-slate-500">Similar to</span>
              <span className="font-medium text-slate-900">{similarDrug.name}</span>
              {similarDrug.similarity !== undefined && (
                <span className="text-xs text-slate-500">
                  Tanimoto {similarDrug.similarity.toFixed(2)}
                </span>
              )}
            </div>
          )}

          {admet && (
            <div className="text-xs text-slate-500 flex flex-wrap gap-3">
              <span>MW {admet.molecular_weight}</span>
              <span>logP {admet.logp}</span>
              <span>HBD {admet.hbd}</span>
              <span>HBA {admet.hba}</span>
              <span>TPSA {admet.tpsa}</span>
              <span className={admet.lipinski_pass ? "text-green-600" : "text-amber-600"}>
                Lipinski {admet.lipinski_pass ? "pass" : "review"}
              </span>
            </div>
          )}

          {explanation && (
            <p className="text-sm text-slate-600 leading-relaxed">
              {explanation}
            </p>
          )}
        </div>
      </div>
    </article>
  );
};

export default MoleculeResultRow;

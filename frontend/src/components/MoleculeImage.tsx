import React from "react";
import { API_BASE_URL } from "../api/client";

interface MoleculeImageProps {
  smiles: string;
  size?: number;
}

const MoleculeImage: React.FC<MoleculeImageProps> = ({
  smiles,
  size = 160,
}) => {
  const url = `${API_BASE_URL}/molecule/image?smiles=${encodeURIComponent(
    smiles
  )}`;

  return (
    <div
      className="flex items-center justify-center rounded-md bg-white"
      style={{ width: size, height: size }}
    >
      <img
        src={url}
        alt="Molecule"
        className="max-w-full max-h-full object-contain"
        loading="lazy"
      />
    </div>
  );
};

export default MoleculeImage;

import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Dashboard from "../pages/Dashboard";
import { mockApi } from "./mockApi";

const baseRoutes = {
  "GET /runs": () => ({ runs: [] }),
  "GET /targets": () => [{ symbol: "EGFR", uniprot_id: "P00533" }, { symbol: "DRD2", uniprot_id: "P14416" }],
};

const mol = (over: any = {}) => ({
  smiles: "CCCCN", score: 0.74, source: "DeepPurposeScorer", notes: "n", similar_drug: null, similar_drug_semantic: null,
  admet: { molecular_weight: 73.1, logp: 0.6, hbd: 1, hba: 1, rotatable_bonds: 1, tpsa: 26, lipinski_violations: 0, lipinski_pass: true },
  compound_id: 12, origin: "generated", evidence_type: "computational_prediction", predicted_kd_nm: 12.5, pkd: 7.9,
  model: "DeepPurpose BindingDB pretrained ensemble", units: "nM", ...over,
});

const response = (molecules: any[]) => ({
  run_id: "run-1", target_id: "EGFR", num_molecules: molecules.length, molecules, status: "completed", seed: 7,
  models: { dti: { model_name: "DeepPurpose BindingDB pretrained ensemble" } },
  metrics: { generation: { validity: 0.66, uniqueness: 0.8, novelty: 1 }, filtered_out_by_physchem: 4 },
});

const renderDash = () => render(<MemoryRouter><Dashboard /></MemoryRouter>);

describe("Discovery page", () => {
  it("offers only the supported targets", async () => {
    mockApi(baseRoutes);
    renderDash();
    const select = await screen.findByLabelText("Target");
    await waitFor(() => expect(select.querySelectorAll("option")).toHaveLength(2));
    expect(Array.from(select.querySelectorAll("option")).map(o => o.textContent)).toEqual(["EGFR", "DRD2"]);
  });

  it("sends the physicochemical filters and seed to the backend", async () => {
    const calls = mockApi({ ...baseRoutes, "POST /discover": () => response([mol()]) });
    const user = userEvent.setup();
    renderDash();
    await screen.findByLabelText("Target");
    await user.type(screen.getByLabelText("Max MW"), "350");
    await user.type(screen.getByLabelText("Max logP"), "3.5");
    await user.type(screen.getByLabelText("Max TPSA"), "90");
    await user.type(screen.getByLabelText("Seed"), "7");
    await user.click(screen.getByText("Run Discovery"));
    await waitFor(() => expect(calls.some(c => c.path === "/discover")).toBe(true));
    expect(calls.find(c => c.path === "/discover")!.body).toMatchObject({
      target_id: "EGFR", lipinski_only: true, max_mw: 350, max_logp: 3.5, max_tpsa: 90, seed: 7,
    });
  });

  it("omits filters that were left blank", async () => {
    const calls = mockApi({ ...baseRoutes, "POST /discover": () => response([mol()]) });
    const user = userEvent.setup();
    renderDash();
    await screen.findByLabelText("Target");
    await user.click(screen.getByText("Run Discovery"));
    await waitFor(() => expect(calls.some(c => c.path === "/discover")).toBe(true));
    const body = calls.find(c => c.path === "/discover")!.body;
    expect(body.max_mw).toBeUndefined();
    expect(body.seed).toBeUndefined();
  });

  it("labels results as generated, computational predictions with the run metrics", async () => {
    mockApi({ ...baseRoutes, "POST /discover": () => response([mol()]) });
    const user = userEvent.setup();
    renderDash();
    await screen.findByLabelText("Target");
    await user.click(screen.getByText("Run Discovery"));
    expect(await screen.findByTestId("run-metrics")).toHaveTextContent(/Seed 7.*validity 66%.*novelty vs\. registry 100%/);
    await user.click(await screen.findByRole("button", { name: "Show details" }));
    expect(await screen.findByTestId("predicted-kd")).toHaveTextContent(/12\.5 nM/);
    expect(screen.getByTestId("predicted-kd")).toHaveTextContent(/not experimentally confirmed/);
    expect(screen.getByText(/open in library/i)).toBeInTheDocument();
  });

  it("explains an empty result instead of showing unfiltered molecules", async () => {
    mockApi({ ...baseRoutes, "POST /discover": () => response([]) });
    const user = userEvent.setup();
    renderDash();
    await screen.findByLabelText("Target");
    await user.click(screen.getByText("Run Discovery"));
    expect(await screen.findByText(/No generated molecule satisfied the selected filters/)).toBeInTheDocument();
  });

  it("shows the backend's reason when the request is rejected or the model fails", async () => {
    mockApi({ ...baseRoutes, "POST /discover": () => ({ __status: 502, body: { detail: "DeepPurpose prediction failed: boom" } }) });
    const user = userEvent.setup();
    renderDash();
    await screen.findByLabelText("Target");
    await user.click(screen.getByText("Run Discovery"));
    expect(await screen.findByText(/DeepPurpose prediction failed: boom/)).toBeInTheDocument();
  });
});

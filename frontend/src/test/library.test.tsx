import { describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { buildQuery, errorMessage } from "../api/library";
import Library from "../pages/Library";
import CompoundProfile from "../pages/CompoundProfile";
import { compound, mockApi, physchem, stats } from "./mockApi";

const list = (items: any[]) => ({ total: items.length, limit: 25, offset: 0, items });

const ITEMS = [
  compound({ id: 1, name: "Aspirin", origin: "reference" }),
  compound({ id: 2, name: null, inchikey: "ZZZZZZZZZZZZZZ-UHFFFAOYSA-N", origin: "generated", n_predictions: 1,
    canonical_smiles: "CCCCN", physchem: physchem({ mol_weight: 73.1, lipinski_pass: true }) }),
  compound({ id: 3, name: "Gefitinib", origin: "external", n_experimental: 2 }),
];

const renderLibrary = (route = "/library") =>
  render(<MemoryRouter initialEntries={[route]}><Routes><Route path="/library" element={<Library />} /></Routes></MemoryRouter>);

describe("api helpers", () => {
  it("buildQuery drops empty values and keeps zeros/false", () => {
    expect(buildQuery({ a: 1, b: undefined, c: "", d: null, e: 0, f: false, g: "x y" })).toBe("?a=1&e=0&f=false&g=x+y");
    expect(buildQuery({})).toBe("");
  });
  it("errorMessage extracts FastAPI detail", () => {
    expect(errorMessage(new Error(JSON.stringify({ detail: "Unsupported target 'X'" })))).toBe("Unsupported target 'X'");
    expect(errorMessage(new Error(JSON.stringify({ detail: [{ msg: "bad k" }] })))).toBe("bad k");
    expect(errorMessage(new Error("plain"))).toBe("plain");
  });
});

describe("Compound Library page", () => {
  it("shows registry stats and compounds with origin badges", async () => {
    mockApi({
      "GET /library/stats": () => stats(),
      "GET /library/compounds": () => list(ITEMS),
      "GET /library/collections": () => [],
    });
    renderLibrary();
    expect(await screen.findByText("Aspirin")).toBeInTheDocument();
    expect(screen.getByTestId("stat-generated")).toHaveTextContent("1");
    const badges = screen.getAllByTestId("origin-badge").map(b => b.textContent);
    expect(badges).toEqual(["Reference", "Generated", "External"]);
    expect(screen.getByText("2 measured")).toBeInTheDocument();
    expect(screen.getByText("1 predicted")).toBeInTheDocument();
  });

  it("every filter control changes the request sent to the backend", async () => {
    const calls = mockApi({
      "GET /library/stats": () => stats(),
      "GET /library/compounds": () => list(ITEMS),
      "GET /library/collections": () => [],
    });
    const user = userEvent.setup();
    renderLibrary();
    await screen.findByText("Aspirin");
    const last = () => calls.filter(c => c.path === "/library/compounds").at(-1)!.query;

    await user.selectOptions(screen.getByLabelText("Origin"), "generated");
    await waitFor(() => expect(last().get("origin")).toBe("generated"));

    await user.type(screen.getByLabelText("Max MW"), "300");
    await waitFor(() => expect(last().get("max_mw")).toBe("300"));
    await user.type(screen.getByLabelText("Min logP"), "1.5");
    await waitFor(() => expect(last().get("min_logp")).toBe("1.5"));
    await user.type(screen.getByLabelText("Max TPSA"), "90");
    await waitFor(() => expect(last().get("max_tpsa")).toBe("90"));
    await user.type(screen.getByLabelText("Max HBD"), "2");
    await waitFor(() => expect(last().get("max_hbd")).toBe("2"));
    await user.type(screen.getByLabelText("Max HBA"), "5");
    await waitFor(() => expect(last().get("max_hba")).toBe("5"));
    await user.type(screen.getByLabelText("Max rotatable bonds"), "4");
    await waitFor(() => expect(last().get("max_rotatable_bonds")).toBe("4"));
    await user.selectOptions(screen.getByLabelText("Lipinski"), "true");
    await waitFor(() => expect(last().get("lipinski_pass")).toBe("true"));
    await user.selectOptions(screen.getByLabelText("Experimental data"), "true");
    await waitFor(() => expect(last().get("has_experimental")).toBe("true"));
    await user.selectOptions(screen.getByLabelText("Predictions"), "true");
    await waitFor(() => expect(last().get("has_prediction")).toBe("true"));
    await user.selectOptions(screen.getByLabelText("Target (for evidence filters)"), "EGFR");
    await waitFor(() => expect(last().get("target")).toBe("EGFR"));
    await user.selectOptions(screen.getByLabelText("Source database"), "elysium_generator");
    await waitFor(() => expect(last().get("source_db")).toBe("elysium_generator"));
    await user.selectOptions(screen.getByLabelText("Sort by"), "mol_weight");
    await user.selectOptions(screen.getByLabelText("Order"), "desc");
    await waitFor(() => { expect(last().get("sort")).toBe("mol_weight"); expect(last().get("order")).toBe("desc"); });
    await user.type(screen.getByLabelText(/Search name/), "gefi");
    await waitFor(() => expect(last().get("q")).toBe("gefi"));

    await user.click(screen.getByRole("button", { name: "Reset" }));
    await waitFor(() => { expect(last().get("origin")).toBeNull(); expect(last().get("max_mw")).toBeNull(); expect(last().get("q")).toBeNull(); });
  });

  it("renders whatever the backend returns after filtering (empty state)", async () => {
    mockApi({
      "GET /library/stats": () => stats(),
      "GET /library/compounds": url => list(url.searchParams.get("max_mw") === "10" ? [] : ITEMS),
      "GET /library/collections": () => [],
    });
    const user = userEvent.setup();
    renderLibrary();
    await screen.findByText("Aspirin");
    await user.type(screen.getByLabelText("Max MW"), "10");
    expect(await screen.findByText("No compounds match these filters.")).toBeInTheDocument();
    expect(screen.queryByText("Aspirin")).not.toBeInTheDocument();
  });

  it("selecting two compounds enables Compare and shows the comparison", async () => {
    const calls = mockApi({
      "GET /library/stats": () => stats(),
      "GET /library/compounds": () => list(ITEMS),
      "GET /library/collections": () => [],
      "POST /library/compare": () => ({
        compounds: [ITEMS[0], ITEMS[2]], tanimoto_matrix: [[1, 0.42], [0.42, 1]],
        per_target: { EGFR: { "1": { experimental_best: null, latest_prediction: null },
                              "3": { experimental_best: { type: "Ki", value_nm: 3, source_db: "chembl" }, latest_prediction: { predicted_kd_nm: 25, pkd: 7.6, model: "M" } } } },
      }),
    });
    const user = userEvent.setup();
    renderLibrary();
    await screen.findByText("Aspirin");
    const compareBtn = screen.getByRole("button", { name: "Compare" });
    expect(compareBtn).toBeDisabled();
    await user.click(screen.getByLabelText("Select Aspirin"));
    expect(compareBtn).toBeDisabled();
    await user.click(screen.getByLabelText("Select Gefitinib"));
    expect(compareBtn).toBeEnabled();
    await user.click(compareBtn);
    expect(await screen.findByLabelText("Tanimoto matrix")).toBeInTheDocument();
    expect(calls.find(c => c.path === "/library/compare")!.body).toEqual({ compound_ids: [1, 3] });
    const evidence = screen.getByLabelText("Evidence for EGFR");
    expect(within(evidence).getByText(/Ki 3\.0 nM/)).toBeInTheDocument();       // experimental
    expect(within(evidence).getByText(/25\.0 nM/)).toBeInTheDocument();             // predicted
    expect(within(evidence).getByText(/computational/)).toBeInTheDocument();
  });

  it("adds selected compounds to a collection", async () => {
    const calls = mockApi({
      "GET /library/stats": () => stats(),
      "GET /library/compounds": () => list(ITEMS),
      "GET /library/collections": () => [{ id: 7, name: "Kinase set", description: null, size: 0 }],
      "POST /library/collections/7/items": () => ({ added: true }),
    });
    const user = userEvent.setup();
    renderLibrary();
    await screen.findByText("Aspirin");
    await user.click(screen.getByLabelText("Select Aspirin"));
    await user.selectOptions(screen.getByLabelText("Collection to add to"), "7");
    await user.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() => expect(calls.filter(c => c.path === "/library/collections/7/items")).toHaveLength(1));
    expect(calls.find(c => c.path === "/library/collections/7/items")!.body).toEqual({ compound_id: 1 });
    expect(await screen.findByRole("status")).toHaveTextContent("Added 1 compound");
  });

  it("similarity search posts the query and lists ranked neighbours", async () => {
    const calls = mockApi({
      "GET /library/stats": () => stats(),
      "POST /library/similarity": () => ({
        query_smiles: "CCO", k: 2, registry_size: 3, notes: {},
        results: { fingerprint: [{ similarity: 0.91, method: "tanimoto", compound: ITEMS[0] }, { similarity: 0.4, method: "tanimoto", compound: ITEMS[2] }] },
      }),
    });
    const user = userEvent.setup();
    renderLibrary("/library?tab=similarity");
    await user.type(await screen.findByLabelText("Query SMILES"), "CCO");
    await user.selectOptions(screen.getByLabelText("Restrict to"), "reference");
    await user.click(screen.getByRole("button", { name: "Search" }));
    const list = await screen.findByLabelText("Similar compounds");
    expect(within(list).getAllByTestId("similarity-value").map(e => e.textContent)).toEqual(["0.910", "0.400"]);
    expect(calls.find(c => c.path === "/library/similarity")!.body).toMatchObject({ smiles: "CCO", k: 10, method: "fingerprint", origin: "reference" });
  });

  it("shows the backend error for an invalid SMILES", async () => {
    mockApi({
      "GET /library/stats": () => stats(),
      "POST /library/similarity": () => ({ __status: 422, body: { detail: "Cannot parse SMILES: 'x'" } }),
    });
    const user = userEvent.setup();
    renderLibrary("/library?tab=similarity");
    await user.type(await screen.findByLabelText("Query SMILES"), "x");
    await user.click(screen.getByRole("button", { name: "Search" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot parse SMILES");
  });

  it("creates a collection from the Collections tab", async () => {
    let created = false;
    const calls = mockApi({
      "GET /library/stats": () => stats(),
      "GET /library/collections": () => (created ? [{ id: 1, name: "Hits", description: null, size: 0 }] : []),
      "POST /library/collections": () => { created = true; return { id: 1, name: "Hits", size: 0 }; },
    });
    const user = userEvent.setup();
    renderLibrary("/library?tab=collections");
    await user.type(await screen.findByLabelText("Name"), "Hits");
    await user.click(screen.getByRole("button", { name: "Create" }));
    expect(await screen.findByText("Hits")).toBeInTheDocument();
    expect(calls.find(c => c.method === "POST")!.body).toMatchObject({ name: "Hits" });
  });

  it("importing a target sends the chosen sources and reports per-source errors", async () => {
    const calls = mockApi({
      "GET /library/stats": () => stats(),
      "GET /library/targets": () => [{ symbol: "EGFR", uniprot_id: "P00533", experimental_measurements: 0, predictions: 0 }],
      "POST /library/import/target": () => ({ target: "EGFR", sources: { chembl: { records: 3, new_compounds: 2, new_bioactivities: 3 } },
                                              errors: { bindingdb: "BindingDB: empty response body" } }),
    });
    const user = userEvent.setup();
    renderLibrary("/library?tab=data");
    await user.click(await screen.findByLabelText("BindingDB"));          // untick BindingDB
    await user.click(screen.getByRole("button", { name: "Import measurements" }));
    const out = await screen.findByTestId("import-result");
    expect(out).toHaveTextContent("new_bioactivities");
    expect(calls.find(c => c.path === "/library/import/target")!.body).toEqual({ target: "EGFR", sources: ["chembl"], max_records: 200 });
  });
});

describe("Compound profile", () => {
  const profile = {
    ...compound({ id: 3, name: "Gefitinib", origin: "reference", n_experimental: 1, n_predictions: 1 }),
    original_smiles: "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1", created_at: "2026-11-02T10:00:00",
    sources_detail: [{ source_db: "chembl", external_id: "CHEMBL939", original_smiles: "COc1...", url: "https://www.ebi.ac.uk/chembl/", retrieved_at: "2026-11-02T10:00:00", note: null }],
    experimental_bioactivity: [{ id: 1, target: "EGFR", uniprot_id: "P00533", source_db: "chembl", external_id: "123", type: "IC50", relation: "=", value_nm: 33, pvalue: 7.48, assay_ref: "CHEMBL1134862", evidence_type: "experimental", retrieved_at: "2026-11-02T10:00:00" }],
    predictions: [{ id: 9, run_id: null, target: "EGFR", uniprot_id: "P00533", model: "DeepPurpose BindingDB pretrained ensemble", model_version: "0.1.5", predicted_kd: 12.5, units: "nM", pkd: 7.9, evidence_type: "computational_prediction", created_at: "2026-11-02T11:00:00" }],
    annotations: [], collections: [], evidence_notice: "experimental_bioactivity = measured values ...; predictions = computational estimates, not experimental confirmation.",
  };

  it("keeps experimental measurements and model predictions in separate, labelled tables", async () => {
    mockApi({
      "GET /library/compounds/3": () => profile,
      "GET /library/collections": () => [],
      "POST /library/similarity": () => ({ query_smiles: "", k: 5, registry_size: 3, notes: {}, results: { fingerprint: [] } }),
    });
    render(<MemoryRouter initialEntries={["/library/3"]}><Routes><Route path="/library/:compoundId" element={<CompoundProfile />} /></Routes></MemoryRouter>);
    const exp = await screen.findByLabelText("Experimental bioactivity");
    expect(within(exp).getByText(/33\.0 nM/)).toBeInTheDocument();
    expect(within(exp).getByText("CHEMBL1134862")).toBeInTheDocument();
    const pred = screen.getByLabelText("Prediction history");
    expect(within(pred).getByText(/12\.5 nM/)).toBeInTheDocument();
    expect(screen.getAllByText(/not experimental confirmation/i).length).toBeGreaterThanOrEqual(2);   // page notice + prediction card
    expect(screen.getByLabelText("Sources")).toHaveTextContent("chembl");
  });

  it("saves an annotation and reloads the profile", async () => {
    let notes: any[] = [];
    const calls = mockApi({
      "GET /library/compounds/3": () => ({ ...profile, annotations: notes }),
      "GET /library/collections": () => [],
      "POST /library/similarity": () => ({ query_smiles: "", k: 5, registry_size: 3, notes: {}, results: { fingerprint: [] } }),
      "POST /library/compounds/3/annotations": (_u, init) => { notes = [{ id: 1, author: "AA", text: JSON.parse(String(init?.body)).text, created_at: "2026-11-02T12:00:00" }]; return notes[0]; },
    });
    const user = userEvent.setup();
    render(<MemoryRouter initialEntries={["/library/3"]}><Routes><Route path="/library/:compoundId" element={<CompoundProfile />} /></Routes></MemoryRouter>);
    await user.type(await screen.findByLabelText("Add a note"), "Hinge binder");
    await user.click(screen.getByRole("button", { name: "Save note" }));
    expect(await screen.findByText("Hinge binder")).toBeInTheDocument();
    expect(calls.find(c => c.path.endsWith("/annotations"))!.body.text).toBe("Hinge binder");
  });

  it("shows an error for a missing compound", async () => {
    mockApi({ "GET /library/compounds/99": () => ({ __status: 404, body: { detail: "Compound 99 not found" } }) });
    render(<MemoryRouter initialEntries={["/library/99"]}><Routes><Route path="/library/:compoundId" element={<CompoundProfile />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("alert")).toHaveTextContent("Compound 99 not found");
  });
});

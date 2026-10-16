async (page) => {
  const apiPath =
    "E:/comfyui/Jev-Decision-Design/plugin/ComfyUI-Jev-Decision/examples/semantic-judge-interop.api.json";
  const workflowPath =
    "E:/comfyui/Jev-Decision-Design/plugin/ComfyUI-Jev-Decision/examples/semantic-judge-interop.workflow.json";

  await page.waitForFunction(
    () =>
      Boolean(
        window.app &&
          window.graph &&
          document.querySelector("#comfy-file-input"),
      ),
    null,
    { timeout: 30000 },
  );
  const fileInput = page.locator("#comfy-file-input");
  await fileInput.setInputFiles(apiPath);
  await page.waitForTimeout(1500);

  const serialized = await page.evaluate(() => window.graph.serialize());
  const downloadPromise = page.waitForEvent("download");
  await page.evaluate((workflow) => {
    const blob = new Blob([`${JSON.stringify(workflow, null, 2)}\n`], {
      type: "application/json",
    });
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(blob);
    anchor.download = "semantic-judge-interop.workflow.json";
    anchor.click();
    URL.revokeObjectURL(anchor.href);
  }, serialized);
  const download = await downloadPromise;
  await download.saveAs(workflowPath);

  await page.evaluate(async () => {
    await window.app.loadGraphData({
      last_node_id: 0,
      last_link_id: 0,
      nodes: [],
      links: [],
      groups: [],
      config: {},
      extra: {},
      version: 0.4,
    });
  });
  await fileInput.setInputFiles([]);
  await fileInput.setInputFiles(workflowPath);
  await page.waitForTimeout(1500);

  const result = await page.evaluate(({ original, savedPath }) => {
    const saved = window.graph.serialize();
    const judge = saved.nodes.find((node) => node.type === "JevSemanticJudge");
    const originalJudge = original.nodes.find(
      (node) => node.type === "JevSemanticJudge",
    );
    const types = saved.nodes.map((node) => node.type).sort();
    const originalTypes = original.nodes.map((node) => node.type).sort();
    const differences = [];
    const compare = (left, right, prefix = "") => {
      if (differences.length >= 30) return;
      if (Object.is(left, right)) return;
      if (
        left === null ||
        right === null ||
        typeof left !== "object" ||
        typeof right !== "object"
      ) {
        differences.push(prefix || "$");
        return;
      }
      const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
      for (const key of keys) {
        compare(left[key], right[key], prefix ? `${prefix}.${key}` : key);
      }
    };
    compare(original, saved);
    return {
      nodeCount: saved.nodes.length,
      linkCount: Array.isArray(saved.links)
        ? saved.links.length
        : Object.keys(saved.links || {}).length,
      types,
      judgeWidgets: judge?.widgets_values ?? null,
      judgeInputLinks: judge?.inputs?.map((input) => ({
        name: input.name,
        type: input.type,
        link: input.link ?? null,
      })) ?? null,
      judgeOutputLinks: judge?.outputs?.map((output) => ({
        name: output.name,
        type: output.type,
        links: output.links ?? [],
      })) ?? null,
      roundTripEqual: JSON.stringify(saved) === JSON.stringify(original),
      preserved: {
        nodeTypes: JSON.stringify(types) === JSON.stringify(originalTypes),
        nodeCount: saved.nodes.length === original.nodes.length,
        linkCount:
          (Array.isArray(saved.links)
            ? saved.links.length
            : Object.keys(saved.links || {}).length) ===
          (Array.isArray(original.links)
            ? original.links.length
            : Object.keys(original.links || {}).length),
        judgeWidgets:
          JSON.stringify(judge?.widgets_values ?? null) ===
          JSON.stringify(originalJudge?.widgets_values ?? null),
        judgeOutputTypes:
          JSON.stringify(
            judge?.outputs?.map((output) => [output.name, output.type]) ?? null,
          ) ===
          JSON.stringify(
            originalJudge?.outputs?.map((output) => [output.name, output.type]) ??
              null,
          ),
        judgeOutputLinkCounts:
          JSON.stringify(
            judge?.outputs?.map((output) => output.links?.length ?? 0) ?? null,
          ) ===
          JSON.stringify(
            originalJudge?.outputs?.map(
              (output) => output.links?.length ?? 0,
            ) ?? null,
          ),
      },
      differencePaths: differences,
      workflowPath: savedPath,
    };
  }, { original: serialized, savedPath: workflowPath });
  const unexpectedDifference = result.differencePaths.find(
    (difference) =>
      difference !== "id" &&
      !difference.endsWith(".properties.ue_properties.version"),
  );
  const contextInput = result.judgeInputLinks?.find(
    (input) =>
      input.name === "context" && input.type.split(",").includes("STRING"),
  );
  if (
    !Object.values(result.preserved).every(Boolean) ||
    !contextInput ||
    contextInput.link === null ||
    unexpectedDifference
  ) {
    throw new Error(
      `Frontend round-trip changed semantic workflow data: ${JSON.stringify(result)}`,
    );
  }
  return result;
}

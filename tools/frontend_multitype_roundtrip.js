async (page) => {
  const apiPath =
    "E:/comfyui/Jev-Decision-Design/plugin/ComfyUI-Jev-Decision/examples/semantic-judge-multitype.api.json";
  const workflowPath =
    "E:/comfyui/Jev-Decision-Design/plugin/ComfyUI-Jev-Decision/examples/semantic-judge-multitype.workflow.json";

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

  const original = await page.evaluate(() => window.graph.serialize());
  const downloadPromise = page.waitForEvent("download");
  await page.evaluate((workflow) => {
    const blob = new Blob([`${JSON.stringify(workflow, null, 2)}\n`], {
      type: "application/json",
    });
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(blob);
    anchor.download = "semantic-judge-multitype.workflow.json";
    anchor.click();
    URL.revokeObjectURL(anchor.href);
  }, original);
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

  const result = await page.evaluate((before) => {
    const after = window.graph.serialize();
    const judge = after.nodes.find((node) => node.type === "JevSemanticJudge");
    const source = after.nodes.find((node) => node.type === "PrimitiveBoolean");
    const context = judge?.inputs?.find((input) => input.name === "context");
    const differences = [];
    const compare = (left, right, prefix = "") => {
      if (differences.length >= 30 || Object.is(left, right)) return;
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
    compare(before, after);
    const linkCount = (workflow) =>
      Array.isArray(workflow.links)
        ? workflow.links.length
        : Object.keys(workflow.links || {}).length;
    return {
      nodeCount: after.nodes.length,
      linkCount: linkCount(after),
      contextInput: context
        ? { name: context.name, type: context.type, link: context.link ?? null }
        : null,
      sourceType: source?.outputs?.[0]?.type ?? null,
      sourceValue: source?.widgets_values?.[0] ?? null,
      preserved: {
        nodeCount: after.nodes.length === before.nodes.length,
        linkCount: linkCount(after) === linkCount(before),
        nodeTypes:
          JSON.stringify(after.nodes.map((node) => node.type).sort()) ===
          JSON.stringify(before.nodes.map((node) => node.type).sort()),
        judgeWidgets:
          JSON.stringify(judge?.widgets_values ?? null) ===
          JSON.stringify(
            before.nodes.find((node) => node.type === "JevSemanticJudge")
              ?.widgets_values ?? null,
          ),
      },
      differencePaths: differences,
    };
  }, original);

  const allowedContextTypes =
    result.contextInput?.type?.split(",").sort() ?? [];
  const expectedTypes = [
    "ARRAY",
    "BOOLEAN",
    "DICT",
    "FLOAT",
    "INT",
    "STRING",
  ];
  const unexpectedDifference = result.differencePaths.find(
    (difference) =>
      difference !== "id" &&
      !difference.endsWith(".properties.ue_properties.version"),
  );
  if (
    !Object.values(result.preserved).every(Boolean) ||
    JSON.stringify(allowedContextTypes) !== JSON.stringify(expectedTypes) ||
    result.contextInput?.link === null ||
    result.sourceType !== "BOOLEAN" ||
    result.sourceValue !== false ||
    unexpectedDifference
  ) {
    throw new Error(
      `Frontend multitype round-trip failed: ${JSON.stringify(result)}`,
    );
  }
  return result;
}

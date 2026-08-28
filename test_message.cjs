const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto("http://localhost:3001/login");
  await page.fill('input[id="username"]', "Eliejosuevargas01@gmail.com");
  await page.fill('input[id="password"]', "280108");
  await page.click('button[type="submit"]');
  await page.waitForTimeout(5000); // Wait for login
  await page.goto("http://localhost:3001/omnichannel");
  await page.waitForSelector('input[placeholder="Digite sua mensagem..."]', { timeout: 15000 }).catch(() => console.log("Input nao encontrado"));
  
  const input = await page.$('input[placeholder="Digite sua mensagem..."]');
  if (input) {
    await input.fill("Teste automatizado do Antigravity!");
    await page.keyboard.press('Enter');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: "/home/eliezer/.gemini/antigravity/brain/612c379d-826d-4fa5-9e38-d1c821de5f56/scratch/msg_test.png" });
    console.log("Mensagem enviada com sucesso!");
  } else {
    console.log("Falha ao abrir chat, input não carregou.");
    await page.screenshot({ path: "/home/eliezer/.gemini/antigravity/brain/612c379d-826d-4fa5-9e38-d1c821de5f56/scratch/msg_test_failed.png" });
  }
  await browser.close();
})();

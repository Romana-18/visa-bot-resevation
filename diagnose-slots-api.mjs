// diagnose-slots-api.mjs - Diagnostic script to see actual Almaviva API response structure
import { chromium } from "playwright";

const EMAIL = process.env.APP_EMAIL || "";
const PASS = process.env.APP_PASS || "";

if (!EMAIL || !PASS) {
  console.error("ERROR: Set APP_EMAIL and APP_PASS environment variables");
  process.exit(1);
}

const OFFICE_ID = 1; // Cairo
const VISA_ID = 3;   // Employment Visa (D)
const SERVICE_LEVEL_ID = 1; // Standard

let authState = { authz: null };

(async () => {
  console.log("🔍 Starting Almaviva Slots API Diagnostic...\n");

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
  });

  const page = await context.newPage();

  // Capture auth token
  page.on("request", (req) => {
    const url = req.url();
    if (!url.includes("egyapi.almaviva-visa.it")) return;
    const h = req.headers();
    const auth = h["authorization"] || h["Authorization"];
    if (auth && /^bearer\s+/i.test(auth)) {
      authState.authz = auth;
      console.log("✅ Authorization token captured");
    }
  });

  console.log("📝 Logging in...");
  await page.goto("https://egy.almaviva-visa.it/");
  await page.getByRole("button").filter({ hasText: "person_outline" }).click();
  await page.getByRole("textbox", { name: "Email" }).fill(EMAIL);
  await page.getByRole("textbox", { name: "Password" }).fill(PASS);
  await page.getByRole("button", { name: /Sign ?In|Login/i }).click();
  await page.waitForLoadState("networkidle").catch(() => {});

  // Wait for auth token
  let waited = 0;
  while (!authState.authz && waited < 15000) {
    await page.waitForTimeout(500);
    waited += 500;
  }

  if (!authState.authz) {
    console.error("❌ Failed to capture authorization token");
    await browser.close();
    process.exit(1);
  }

  console.log("\n🔍 Testing Slots API...\n");

  // Test different date ranges
  const today = new Date();
  const dates = [];
  for (let i = 0; i < 14; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    dates.push(d.toISOString().split("T")[0]); // YYYY-MM-DD
  }

  let foundSlots = false;

  for (const dateISO of dates) {
    // Try with service level
    const url1 = `https://egyapi.almaviva-visa.it/reservation-manager/api/slots/v1/free?officeId=${OFFICE_ID}&visaId=${VISA_ID}&serviceLevelId=${SERVICE_LEVEL_ID}&date=${dateISO}&quantity=1&type=WEB`;
    
    console.log(`\n📅 Testing date: ${dateISO}`);
    console.log(`🔗 URL: ${url1}`);

    try {
      const response = await page.request.get(url1, {
        headers: {
          Accept: "application/json, text/plain, */*",
          Authorization: authState.authz,
          "X-Tenant": "EGY",
          "X-Requested-With": "XMLHttpRequest",
          Origin: "https://egy.almaviva-visa.it",
          Referer: "https://egy.almaviva-visa.it/",
        },
        timeout: 30000,
      });

      const status = response.status();
      console.log(`📊 Status: ${status}`);

      if (status === 200) {
        const body = await response.json();
        
        if (Array.isArray(body) && body.length > 0) {
          foundSlots = true;
          console.log(`\n✅ FOUND ${body.length} SLOTS!\n`);
          console.log("=" .repeat(80));
          console.log("FULL API RESPONSE:");
          console.log("=" .repeat(80));
          console.log(JSON.stringify(body, null, 2));
          console.log("=" .repeat(80));
          
          console.log("\n📋 SLOT STRUCTURE ANALYSIS:");
          console.log("=" .repeat(80));
          
          const firstSlot = body[0];
          console.log("\n🔑 Available fields in first slot:");
          console.log(Object.keys(firstSlot));
          
          console.log("\n📝 Field values:");
          for (const [key, value] of Object.entries(firstSlot)) {
            console.log(`  ${key}: ${JSON.stringify(value)}`);
          }
          
          console.log("\n⏰ TIME EXTRACTION ATTEMPTS:");
          const timeFields = [
            "startTime", "start", "slotStartTime", "time", "dateTime", 
            "slotTime", "from", "startDate", "appointmentTime"
          ];
          
          for (const field of timeFields) {
            if (firstSlot[field] !== undefined) {
              console.log(`  ✓ ${field}: ${JSON.stringify(firstSlot[field])}`);
            }
          }
          
          console.log("\n" + "=" .repeat(80));
          
          // Show all slot times
          console.log("\n📅 ALL AVAILABLE TIMES:");
          body.forEach((slot, idx) => {
            const timeValue = slot.startTime || slot.start || slot.time || slot.dateTime || "UNKNOWN";
            console.log(`  Slot ${idx + 1}: ${timeValue}`);
          });
          
          break; // Stop after finding first date with slots
        } else {
          console.log(`  ℹ️  No slots available`);
        }
      } else if (status === 429) {
        console.log(`  ⚠️  Rate limited, waiting...`);
        await page.waitForTimeout(2000);
      } else {
        console.log(`  ⚠️  Unexpected status: ${status}`);
      }
    } catch (error) {
      console.error(`  ❌ Error: ${error.message}`);
    }

    await page.waitForTimeout(500); // Small delay between requests
  }

  if (!foundSlots) {
    console.log("\n❌ No slots found in the next 14 days");
    console.log("💡 Try:");
    console.log("   1. Different visa types");
    console.log("   2. Different offices (Alexandria = 2)");
    console.log("   3. Without serviceLevelId parameter");
  }

  console.log("\n✅ Diagnostic complete!");
  await browser.close();
})().catch((err) => {
  console.error("❌ Fatal error:", err);
  process.exit(1);
});

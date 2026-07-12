// test-time-extraction.mjs - Test time extraction logic with sample data

// Sample slot data from different possible API formats
const testSlots = [
  // Format 1: ISO timestamp with timezone
  {
    id: 1,
    startTime: "2025-01-15T09:00:00+02:00",
    endTime: "2025-01-15T09:30:00+02:00"
  },
  // Format 2: ISO timestamp UTC
  {
    id: 2,
    start: "2025-01-15T07:00:00Z",
    end: "2025-01-15T07:30:00Z"
  },
  // Format 3: Time only string
  {
    id: 3,
    time: "10:30:00",
    date: "2025-01-15"
  },
  // Format 4: Nested object
  {
    id: 4,
    slot: {
      startTime: "2025-01-15T11:00:00+02:00"
    }
  },
  // Format 5: Different field name
  {
    id: 5,
    appointmentTime: "2025-01-15T14:30:00+02:00"
  },
  // Format 6: Unix timestamp (milliseconds)
  {
    id: 6,
    dateTime: 1705315200000 // 2025-01-15 10:00:00 UTC
  },
  // Format 7: Just HH:MM
  {
    id: 7,
    slotTime: "15:00"
  }
];

// Time extraction function (same as in visa-bot.js)
const fmtHM = (v) => {
  try {
    if (!v) return null;
    
    // Handle string with time pattern (HH:MM or HH:MM:SS)
    if (typeof v === "string") {
      // Try to extract time from ISO string or time-only string
      const timeMatch = v.match(/(\d{2}:\d{2}(?::\d{2})?)/);
      if (timeMatch) return timeMatch[1].slice(0, 5); // Return HH:MM only
    }
    
    // Handle Date object or timestamp
    const d = new Date(v);
    if (!isNaN(+d)) {
      // Format in Cairo timezone
      return d.toLocaleTimeString("en-GB", { 
        timeZone: "Africa/Cairo", 
        hour: "2-digit", 
        minute: "2-digit",
        hour12: false 
      });
    }
  } catch (e) {
    console.log(`[WARN] Failed to parse time from:`, v, e.message);
  }
  return null;
};

const getTimeFromSlot = (s) => {
  if (!s || typeof s !== "object") return null;
  
  // Try common field names in order of likelihood
  const candidates = [
    s.startTime,
    s.start,
    s.slotStartTime,
    s.time,
    s.dateTime,
    s.slotTime,
    s.from,
    s.startDate,
    s.appointmentTime,
    s.slot?.startTime,
    s.slot?.start,
  ];
  
  for (const candidate of candidates) {
    const formatted = fmtHM(candidate);
    if (formatted) return formatted;
  }
  
  return null;
};

// Run tests
console.log("🧪 Testing Time Extraction Logic\n");
console.log("=" .repeat(60));

testSlots.forEach((slot, idx) => {
  console.log(`\nTest ${idx + 1}: Slot ID ${slot.id}`);
  console.log("Input:", JSON.stringify(slot, null, 2));
  
  const extractedTime = getTimeFromSlot(slot);
  
  if (extractedTime) {
    console.log(`✅ Extracted time: ${extractedTime}`);
  } else {
    console.log(`❌ Failed to extract time`);
  }
  
  console.log("-" .repeat(60));
});

console.log("\n📊 Summary:");
const successful = testSlots.filter(s => getTimeFromSlot(s) !== null).length;
console.log(`✅ Successfully extracted: ${successful}/${testSlots.length}`);
console.log(`❌ Failed: ${testSlots.length - successful}/${testSlots.length}`);

if (successful === testSlots.length) {
  console.log("\n🎉 All tests passed! Time extraction is working correctly.");
} else {
  console.log("\n⚠️  Some tests failed. Check the logic for those formats.");
}

// Test with your actual API response
console.log("\n" + "=" .repeat(60));
console.log("📝 To test with your actual API response:");
console.log("=" .repeat(60));
console.log(`
1. Run: node diagnose-slots-api.mjs
2. Copy the JSON from "[DEBUG] First slot structure:"
3. Add it to this file as a new test case
4. Run: node test-time-extraction.mjs
`);

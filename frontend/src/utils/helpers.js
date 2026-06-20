export const PRESETS = {
  car: {
    claimId: 'CLM-2024-CAR-001',
    objectType: 'car',
    minEvidence: 1,
    conversation: [
      { role: 'user', text: 'I need to file a claim for damage to my car.' },
      { role: 'agent', text: 'I can help. What type of damage occurred?' },
      { role: 'user', text: 'Someone hit my rear bumper in a parking lot. There is a significant dent and paint scratches on the right side.' },
      { role: 'agent', text: 'Please upload photos of the damage so we can assess your claim.' },
    ],
    history: { total: 2, approved: 2, rejected: 0, fraud: 0, age: 730, risk: 0.15 },
  },
  laptop: {
    claimId: 'CLM-2024-LAPTOP-002',
    objectType: 'laptop',
    minEvidence: 2,
    conversation: [
      { role: 'user', text: 'My laptop screen cracked after it fell off my desk.' },
      { role: 'agent', text: 'How did the fall occur and what exactly is damaged?' },
      { role: 'user', text: 'It fell about 3 feet onto hardwood floor. Screen has a large crack and dead pixels. Chassis corner is also bent.' },
      { role: 'agent', text: 'Please provide photos showing the screen damage and impact point.' },
    ],
    history: { total: 5, approved: 3, rejected: 2, fraud: 1, age: 365, risk: 0.62 },
  },
  package: {
    claimId: 'CLM-2024-PKG-003',
    objectType: 'package',
    minEvidence: 1,
    conversation: [
      { role: 'user', text: 'My package arrived severely damaged.' },
      { role: 'agent', text: 'What does the damage look like?' },
      { role: 'user', text: 'Box is completely crushed on one side and the ceramic vase inside is broken. Tape looks cut and resealed.' },
      { role: 'agent', text: 'Upload images of the outer packaging and damaged contents.' },
    ],
    history: { total: 0, approved: 0, rejected: 0, fraud: 0, age: 180, risk: 0.05 },
  },
}

export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result.split(',')[1])
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export function genImageId(index) {
  return `IMG-${Date.now().toString(36).toUpperCase()}-${index}`
}

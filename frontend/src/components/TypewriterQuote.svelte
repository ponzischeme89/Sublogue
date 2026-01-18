<script>
  import { onMount, onDestroy } from "svelte";

  export let style = "sarcastic";

  const quotes = {
    sarcastic: [
      "Oh, you're still here? How delightful.",
      "Scanning... because apparently you have nothing better to do.",
      "Looking for subtitles like it's 2005.",
      "This is fine. Everything is fine.",
      "Patience is a virtue you clearly possess.",
      "Working hard or hardly working? Same thing here.",
      "Your files aren't going anywhere. Neither am I.",
      "Just vibing while your CPU does the heavy lifting.",
      "One does not simply scan quickly.",
      "Plot twist: the subtitles were inside you all along.",
      "Loading... your patience.",
      "This scan is sponsored by existential dread.",
    ],
    rude: [
      "Ugh, more files? What did you do, collect them competitively?",
      "You could've organized these better. You actively chose not to.",
      "Why are there so many files? Therapy is cheaper.",
      "I don't get paid enough for this. Actually, I don't get paid at all.",
      "Your naming conventions aren’t just bad — they’re offensive.",
      "This is taking forever because you live like this.",
      "I’ve seen better file structures in a crime scene.",
      "Oh great, another scan. Thrilling. Electrifying. Life-changing.",
      "Do you even know what you're looking for, or are we just clicking things now?",
      "These files are judging you. Loudly.",
      "Scanning your deeply questionable life choices.",
      "I hope you appreciate this. Statistically, you won’t.",
    ],
    nice: [
      "Taking a moment to find your perfect subtitles.",
      "Good things come to those who wait.",
      "Every great movie deserves great subtitles.",
      "Preparing something wonderful for you.",
      "Almost there! Thanks for your patience.",
      "Finding the best matches just for you.",
      "Your movie night is about to get better.",
      "Working diligently behind the scenes.",
      "Great content is worth the wait.",
      "Making movie magic happen.",
      "Your subtitles are in good hands.",
      "Sit back and relax, we've got this.",
    ],
  };

  let displayedText = "";
  let animationFrame;
  let currentTimeout;
  let usedIndices = [];
  let isTyping = true;
  let mounted = false;

  function getRandomQuote() {
    const styleQuotes = quotes[style] || quotes.sarcastic;

    if (usedIndices.length >= styleQuotes.length) {
      usedIndices = [];
    }

    let idx;
    do {
      idx = Math.floor(Math.random() * styleQuotes.length);
    } while (usedIndices.includes(idx));

    usedIndices.push(idx);
    return styleQuotes[idx];
  }

  function typeText(text, onComplete) {
    let index = 0;
    isTyping = true;

    function typeNext() {
      if (!mounted) return;

      if (index <= text.length) {
        displayedText = text.slice(0, index);
        index++;
        // Variable speed: faster for spaces, slower for punctuation
        const char = text[index - 1];
        let delay = 45;
        if (char === " ") delay = 25;
        else if ([".", ",", "!", "?"].includes(char)) delay = 120;

        currentTimeout = setTimeout(() => {
          animationFrame = requestAnimationFrame(typeNext);
        }, delay);
      } else {
        isTyping = false;
        currentTimeout = setTimeout(onComplete, 2500);
      }
    }

    animationFrame = requestAnimationFrame(typeNext);
  }

  function eraseText(onComplete) {
    isTyping = false;

    function eraseNext() {
      if (!mounted) return;

      if (displayedText.length > 0) {
        displayedText = displayedText.slice(0, -1);
        currentTimeout = setTimeout(() => {
          animationFrame = requestAnimationFrame(eraseNext);
        }, 20);
      } else {
        currentTimeout = setTimeout(onComplete, 200);
      }
    }

    animationFrame = requestAnimationFrame(eraseNext);
  }

  function runCycle() {
    if (!mounted) return;
    const quote = getRandomQuote();
    typeText(quote, () => {
      if (!mounted) return;
      eraseText(() => {
        if (!mounted) return;
        runCycle();
      });
    });
  }

  function cleanup() {
    if (animationFrame) cancelAnimationFrame(animationFrame);
    if (currentTimeout) clearTimeout(currentTimeout);
  }

  onMount(() => {
    mounted = true;
    runCycle();
  });

  onDestroy(() => {
    mounted = false;
    cleanup();
  });

  // Handle style changes
  let prevStyle = style;
  $: if (mounted && style !== prevStyle) {
    prevStyle = style;
    cleanup();
    usedIndices = [];
    displayedText = "";
    runCycle();
  }
</script>

<p class="text-[13px] text-text-secondary mb-1 min-h-[1.5em]">
  {displayedText}<span
    class="inline-block w-[2px] h-[1em] bg-text-secondary ml-[1px] align-middle"
    class:animate-blink={!isTyping}
  ></span>
</p>

<style>
  @keyframes blink {
    0%,
    50% {
      opacity: 1;
    }
    51%,
    100% {
      opacity: 0;
    }
  }
  .animate-blink {
    animation: blink 1s infinite;
  }
</style>

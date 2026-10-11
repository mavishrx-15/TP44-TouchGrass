# Community content filters

Photos use NSFWJS MobileNetV2, the image classifier also supported by
https://github.com/nsfw-filter/nsfw-filter. The extension itself is not embedded.
The model is bundled with the npm package and loaded lazily, without sending
photos to a third-party moderation API. A combined Porn/Hentai/Sexy probability
of 0.5 or more blocks uploads. Failed checks block uploads too; users can retry
or proceed without a photo. Approved community photos are checked before display;
unsafe photos or failed checks omit the photo while retaining the message.

The backend applies a basic English/Chinese word and phrase filter to messages,
damage reports, approvals, and existing public messages. It normalizes full-width
text, invisible characters and some common character substitutions. This is a
limited word filter, not comprehensive multilingual abuse detection.

All submissions still require the existing administrator approval before public
display. Browser classification can be bypassed by direct API clients and is not
server-side image moderation. Keep the approval requirement; automatic public
publishing would require a trusted server-side classifier. Models can make mistakes.

Run backend care/content-filter tests and frontend moderation tests after changes.

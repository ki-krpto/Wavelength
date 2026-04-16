---
permalink: /mirroring.html
---
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>Wavelength Mirrors</title>
	<link rel="stylesheet" href="styles.css">
	<link rel="icon" href="./assets/icon-noborder.png">
</head>
<body>
	<div class="window centered" style="margin-top:32px;">
		<div class="title-bar">
			<img src="assets/icon-noborder.png" alt="logo" class="title-icon">
			<span>WAVELENGTH MIRRORS</span>
		</div>
		<div class="content" style="max-width:600px;margin:auto;">
			<div class="panel" style="margin:24px auto 0 auto;">
				<div class="panel-header">&#9670; Mirror Links</div>
				<div class="panel-body">
					<p class="note" style="margin-bottom:12px;">Alternate links if you can't access the main site or it gets blocked.</p>
					<ul id="mirrors-list" style="margin-bottom:12px;">
						<li><a href="https://wavelength.rip" target="_blank">wavelength.rip</a> - main mirror (thanks ThatOnePers0n!)</li>
						<li><a href="https://wavelength-real.pages.dev" target="_blank">wavelength-real.pages.dev</a> - Cloudflare Pages mirror</li>
						<li><a href="https://wavelength-8vk.pages.dev" target="_blank">wavelength-8vk.pages.dev</a> - main site</li>
					</ul>
					<p style="font-size:12px;opacity:0.8;">All mirrors update every 7 minutes. If you want to make your own, see below!</p>
				</div>
			</div>
			<div class="panel" style="margin:24px auto 0 auto;">
				<div class="panel-header">&#9670; Make Your Own Mirror</div>
				<div class="panel-body">
					<b>Cloudflare Pages:</b>
					<ol style="margin-bottom:10px;">
						<li>Fork the repository on GitHub</li>
						<li>Deploy to Cloudflare Pages</li>
						<li>Set build command to <code>npm run start</code></li>
						<li>Workflow keeps your fork up to date every 7 minutes</li>
					</ol>
					<b>GitHub Pages:</b>
					<ol>
						<li>Fork the repository</li>
						<li>Go to <b>Settings</b> &rarr; <b>Pages</b></li>
						<li>Under "Build and deployment", select GitHub Actions</li>
						<li>Done! (not as tested, but should work)</li>
					</ol>
				</div>
			</div>
		</div>
	</div>
</body>
</html>
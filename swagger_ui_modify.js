(async () => {
	// ============================================================
	// Configuration
	// ============================================================

	const OPENAPI_URL = "/openapi.json";


	// ============================================================
	// Load WebSocket definitions
	// ============================================================

	const schema = await fetch(OPENAPI_URL).then(response => response.json());

	const websocketEndpoints = [];

	for (const [path, definition] of Object.entries(schema.paths ?? {})) {
		const websocket = definition["x-websocket"];

		if (!websocket)
			continue;

		websocketEndpoints.push({
			path,
			...websocket
		});
	}

	if (websocketEndpoints.length === 0)
		return;


	// ============================================================
	// Wait until Swagger UI has rendered its operation groups
	// ============================================================

	const waitForSwagger = setInterval(() => {
		const swagger = document.querySelector("#swagger-ui .swagger-ui");

		if (!swagger)
			return;

		const tagSections = swagger.querySelectorAll(
			".opblock-tag-section"
		);

		if (tagSections.length === 0)
			return;

		clearInterval(waitForSwagger);

		for (const endpoint of websocketEndpoints) {
			insertWebSocketEndpoint(
				endpoint,
				tagSections
			);
		}
	}, 50);


	// ============================================================
	// Insert WebSocket into its Swagger tag/category
	// ============================================================

	function insertWebSocketEndpoint(endpoint, tagSections) {
		const tags =
			Array.isArray(endpoint.tags) &&
			endpoint.tags.length > 0
				? endpoint.tags
				: ["default"];

		const tag = tags[0];

		const targetSection = findTagSection(
			tag,
			tagSections
		);

		if (!targetSection) {
			console.warn(
				`Swagger UI: could not find tag "${tag}" ` +
				`for WebSocket ${endpoint.path}`
			);

			return;
		}

		const operationId = createOperationId(
			tag,
			endpoint.path
		);

		// Prevent duplicates in case this script is somehow
		// executed more than once.
		if (document.getElementById(operationId))
			return;

		const block = createWebSocketBlock(
			endpoint,
			tag,
			operationId
		);

		/*
		 * Swagger's operations are direct children of the
		 * .opblock-tag-section after the tag heading.
		 *
		 * Appending here therefore places WS alongside GET,
		 * POST, DELETE, etc.
		 */
		targetSection.appendChild(block);
	}


	// ============================================================
	// Find existing Swagger category
	// ============================================================

	function findTagSection(tag, tagSections) {
		for (const section of tagSections) {
			const heading = section.querySelector(
				":scope > .opblock-tag"
			);

			if (!heading)
				continue;

			/*
			 * Swagger's heading can contain the tag name,
			 * description, icons, etc.
			 *
			 * Prefer the first obvious tag-name element.
			 */
			const nameElement =
				heading.querySelector(".nostyle span") ??
				heading.querySelector(".nostyle");

			if (
				nameElement?.textContent?.trim() === tag
			) {
				return section;
			}

			/*
			 * Fallback:
			 * the tag name is normally the first text node.
			 */
			for (const node of heading.childNodes) {
				if (
					node.nodeType === Node.TEXT_NODE &&
					node.textContent.trim() === tag
				) {
					return section;
				}
			}
		}

		return null;
	}


	// ============================================================
	// Create WebSocket operation
	// ============================================================

	function createWebSocketBlock(
		endpoint,
		tag,
		operationId
	) {
		// --------------------------------------------------------
		// Root
		// --------------------------------------------------------

		const block = document.createElement("div");

		block.id = operationId;
		block.className = "opblock opblock-ws";


		// --------------------------------------------------------
		// Summary
		// --------------------------------------------------------

		const summary = document.createElement("div");

		summary.className =
			"opblock-summary opblock-summary-ws";


		// --------------------------------------------------------
		// Main summary control
		// --------------------------------------------------------

		const summaryControl =
			document.createElement("button");

		summaryControl.type = "button";
		summaryControl.className =
			"opblock-summary-control";

		summaryControl.setAttribute(
			"aria-expanded",
			"false"
		);


		// WS method label

		const method = document.createElement("span");

		method.className = "opblock-summary-method";
		method.textContent = "WS";


		// Path + summary description wrapper

		const pathDescriptionWrapper =
			document.createElement("div");

		pathDescriptionWrapper.className =
			"opblock-summary-path-description-wrapper";


		// Path

		const path = document.createElement("span");

		path.className = "opblock-summary-path";
		path.dataset.path = endpoint.path;


		const pathLink = document.createElement("a");

		pathLink.className = "nostyle";
		pathLink.href = `#${operationId}`;


		pathLink.appendChild(
			createSwaggerPathText(endpoint.path)
		);


		path.appendChild(pathLink);


		// Summary

		const description =
			document.createElement("div");

		description.className =
			"opblock-summary-description";

		description.textContent =
			endpoint.summary ?? "";


		pathDescriptionWrapper.appendChild(path);
		pathDescriptionWrapper.appendChild(description);

		summaryControl.appendChild(method);
		summaryControl.appendChild(
			pathDescriptionWrapper
		);


		// --------------------------------------------------------
		// Copy path
		// --------------------------------------------------------

		const copyWrapper =
			createCopyPathButton(endpoint.path);


		// --------------------------------------------------------
		// Expand/collapse arrow
		// --------------------------------------------------------

		const arrowButton =
			createArrowButton(endpoint.path);


		// --------------------------------------------------------
		// Assemble summary
		// --------------------------------------------------------

		summary.appendChild(summaryControl);
		summary.appendChild(copyWrapper);
		summary.appendChild(arrowButton);


		// --------------------------------------------------------
		// Expanded body
		// --------------------------------------------------------

		const body = createWebSocketBody(endpoint);

		body.hidden = true;


		block.appendChild(summary);
		block.appendChild(body);


		// --------------------------------------------------------
		// Expand / collapse behavior
		// --------------------------------------------------------

		function setExpanded(expanded) {
			body.hidden = !expanded;

			block.classList.toggle(
				"is-open",
				expanded
			);

			summaryControl.setAttribute(
				"aria-expanded",
				String(expanded)
			);

			arrowButton.setAttribute(
				"aria-expanded",
				String(expanded)
			);

			const arrowSvg =
				arrowButton.querySelector("svg");

			if (arrowSvg) {
				arrowSvg.style.transform =
					expanded
						? "rotate(180deg)"
						: "";
			}
		}


		function toggleExpanded() {
			setExpanded(body.hidden);
		}


		summaryControl.addEventListener(
			"click",
			event => {
				event.preventDefault();

				toggleExpanded();
			}
		);


		arrowButton.addEventListener(
			"click",
			event => {
				event.preventDefault();
				event.stopPropagation();

				toggleExpanded();
			}
		);


		/*
		 * Don't allow clicking the visual path link itself
		 * to change the page/hash independently.
		 *
		 * The surrounding summary button handles expansion.
		 */
		pathLink.addEventListener(
			"click",
			event => {
				event.preventDefault();
			}
		);


		return block;
	}


	// ============================================================
	// Swagger-style path
	//
	// /v1/news_ws becomes:
	//
	// <span>
	//     /v1
	//     <wbr>
	//     /news_ws
	// </span>
	// ============================================================

	function createSwaggerPathText(path) {
		const span = document.createElement("span");

		const parts = path
			.split("/")
			.filter(Boolean);

		parts.forEach((part, index) => {
			span.append(`/${part}`);

			if (index < parts.length - 1) {
				span.appendChild(
					document.createElement("wbr")
				);
			}
		});

		/*
		 * Edge case for "/"
		 */
		if (parts.length === 0)
			span.textContent = "/";

		return span;
	}


	// ============================================================
	// Copy path button
	// ============================================================

	function createCopyPathButton(path) {
		const wrapper = document.createElement("div");

		wrapper.className =
			"view-line-link copy-to-clipboard";

		wrapper.title = "Copy path to clipboard";

		wrapper.setAttribute(
			"aria-label",
			"Copy path to clipboard"
		);


		const button = document.createElement("button");

		button.type = "button";

		button.setAttribute(
			"aria-label",
			"Copy path to clipboard"
		);


		/*
		 * The exact SVG isn't important to Swagger's layout,
		 * but matching its 15x16 dimensions keeps alignment
		 * consistent with the native control.
		 */
		button.innerHTML = `
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
				width="15"
				height="16"
				aria-hidden="true"
				focusable="false"
			>
				<path
					fill="currentColor"
					d="
						M16 1H4
						c-1.1 0-2 .9-2 2
						v14h2V3h12V1z

						M19 5H8
						c-1.1 0-2 .9-2 2
						v14
						c0 1.1.9 2 2 2
						h11
						c1.1 0 2-.9 2-2
						V7
						c0-1.1-.9-2-2-2z

						M19 21H8V7h11v14z
					"
				/>
			</svg>
		`;


		button.addEventListener(
			"click",
			async event => {
				event.preventDefault();
				event.stopPropagation();

				try {
					await navigator.clipboard.writeText(
						path
					);

					const oldTitle = wrapper.title;

					wrapper.title = "Copied";

					setTimeout(() => {
						wrapper.title = oldTitle;
					}, 1000);
				}
				catch (error) {
					console.error(
						"Could not copy WebSocket path:",
						error
					);
				}
			}
		);


		wrapper.appendChild(button);

		return wrapper;
	}


	// ============================================================
	// Arrow
	// ============================================================

	function createArrowButton(path) {
		const button = document.createElement("button");

		button.type = "button";
		button.className = "opblock-control-arrow";
		button.tabIndex = -1;

		button.setAttribute(
			"aria-label",
			`ws ${path}`
		);

		button.setAttribute(
			"aria-expanded",
			"false"
		);


		/*
		 * Close approximation of Swagger's arrow.
		 *
		 * It uses the same class="arrow", so existing Swagger
		 * styling can affect it where applicable.
		 */
		button.innerHTML = `
			<svg
				class="arrow"
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				width="20"
				height="20"
				aria-hidden="true"
				focusable="false"
			>
				<path
					fill="currentColor"
					d="
						M5.5 7.5
						L10 12
						l4.5-4.5
						1.4 1.4
						-5.9 5.9
						-5.9-5.9
						1.4-1.4z
					"
				/>
			</svg>
		`;

		return button;
	}


	// ============================================================
	// Expanded WebSocket body
	// ============================================================

	function createWebSocketBody(endpoint) {
		const body = document.createElement("div");

		body.className = "opblock-body";


		// --------------------------------------------------------
		// Description
		// --------------------------------------------------------

		if (endpoint.description) {
			const descriptionWrapper =
				document.createElement("div");

			descriptionWrapper.className =
				"opblock-description-wrapper";


			const markdown =
				document.createElement("div");

			markdown.className = "renderedMarkdown";


			const paragraph =
				document.createElement("p");

			paragraph.textContent =
				endpoint.description;


			markdown.appendChild(paragraph);

			descriptionWrapper.appendChild(markdown);

			body.appendChild(descriptionWrapper);
		}


		// --------------------------------------------------------
		// Connection section
		// --------------------------------------------------------

		const connectionHeader =
			createSectionHeader("WebSocket connection");

		body.appendChild(connectionHeader);


		const connectionContainer =
			document.createElement("div");

		connectionContainer.className =
			"websocket-connection-container";


		const connectionControls =
			document.createElement("div");

		connectionControls.className =
			"websocket-controls";


		const connectButton =
			document.createElement("button");

		connectButton.type = "button";
		connectButton.className =
			"btn execute websocket-connect";

		connectButton.textContent = "Connect";


		const disconnectButton =
			document.createElement("button");

		disconnectButton.type = "button";
		disconnectButton.className =
			"btn websocket-disconnect";

		disconnectButton.textContent = "Disconnect";
		disconnectButton.disabled = true;


		const status =
			document.createElement("span");

		status.className =
			"websocket-status websocket-status-disconnected";

		status.textContent = "Disconnected";


		connectionControls.appendChild(
			connectButton
		);

		connectionControls.appendChild(
			disconnectButton
		);

		connectionControls.appendChild(status);

		connectionContainer.appendChild(
			connectionControls
		);


		// --------------------------------------------------------
		// URL
		// --------------------------------------------------------

		const urlRow = document.createElement("div");

		urlRow.className = "websocket-url-row";


		const urlLabel = document.createElement("strong");

		urlLabel.textContent = "URL";


		const urlValue = document.createElement("code");

		urlValue.textContent =
			createWebSocketUrl(endpoint.path);


		urlRow.appendChild(urlLabel);
		urlRow.appendChild(urlValue);

		connectionContainer.appendChild(urlRow);

		body.appendChild(connectionContainer);


		// --------------------------------------------------------
		// Messages
		// --------------------------------------------------------

		body.appendChild(
			createSectionHeader("Messages")
		);


		const messagesContainer =
			document.createElement("div");

		messagesContainer.className =
			"websocket-messages-container";


		const output = document.createElement("pre");

		output.className = "websocket-output";
		output.textContent =
			"No messages received.";


		messagesContainer.appendChild(output);
		body.appendChild(messagesContainer);


		// --------------------------------------------------------
		// Actual WebSocket state
		// --------------------------------------------------------

		let socket = null;


		function setStatus(state, text) {
			status.classList.remove(
				"websocket-status-disconnected",
				"websocket-status-connecting",
				"websocket-status-connected",
				"websocket-status-error"
			);

			status.classList.add(
				`websocket-status-${state}`
			);

			status.textContent = text;
		}


		function resetButtons() {
			connectButton.disabled = false;
			disconnectButton.disabled = true;
		}


		connectButton.addEventListener(
			"click",
			event => {
				event.preventDefault();
				event.stopPropagation();

				if (socket)
					return;

				const url =
					createWebSocketUrl(endpoint.path);

				setStatus(
					"connecting",
					"Connecting..."
				);

				connectButton.disabled = true;

				output.textContent =
					`Connecting to ${url}...`;

				socket = new WebSocket(url);


				// --------------------------------------------
				// Connected
				// --------------------------------------------

				socket.addEventListener(
					"open",
					() => {
						setStatus(
							"connected",
							"Connected"
						);

						connectButton.disabled = true;
						disconnectButton.disabled = false;

						output.textContent =
							"Connected. Waiting for messages...";
					}
				);


				// --------------------------------------------
				// Message received
				// --------------------------------------------

				socket.addEventListener(
					"message",
					event => {
						if (
							output.textContent ===
							"Connected. Waiting for messages..."
						) {
							output.textContent = "";
						}

						const message =
							formatWebSocketMessage(
								event.data
							);

						appendOutput(
							output,
							message
						);
					}
				);


				// --------------------------------------------
				// Error
				// --------------------------------------------

				socket.addEventListener(
					"error",
					() => {
						setStatus(
							"error",
							"Error"
						);
					}
				);


				// --------------------------------------------
				// Disconnected
				// --------------------------------------------

				socket.addEventListener(
					"close",
					event => {
						setStatus(
							"disconnected",
							"Disconnected"
						);

						resetButtons();

						socket = null;

						const suffix =
							event.reason
								? `: ${event.reason}`
								: "";

						appendOutput(
							output,
							`Connection closed (${event.code})${suffix}.`
						);
					}
				);
			}
		);


		disconnectButton.addEventListener(
			"click",
			event => {
				event.preventDefault();
				event.stopPropagation();

				if (
					socket &&
					(
						socket.readyState ===
							WebSocket.OPEN ||
						socket.readyState ===
							WebSocket.CONNECTING
					)
				) {
					socket.close();
				}
			}
		);


		return body;
	}


	// ============================================================
	// Swagger-style section header
	// ============================================================

	function createSectionHeader(title) {
		const header = document.createElement("div");

		header.className = "opblock-section-header";


		const heading = document.createElement("h4");

		heading.textContent = title;


		header.appendChild(heading);

		return header;
	}


	// ============================================================
	// Build ws:// or wss:// URL
	// ============================================================

	function createWebSocketUrl(path) {
		const protocol =
			window.location.protocol === "https:"
				? "wss:"
				: "ws:";

		return `${protocol}//${window.location.host}${path}`;
	}


	// ============================================================
	// Message formatting
	// ============================================================

	function formatWebSocketMessage(data) {
		if (typeof data !== "string")
			return String(data);

		try {
			const json = JSON.parse(data);

			return JSON.stringify(
				json,
				null,
				2
			);
		}
		catch {
			return data;
		}
	}


	// ============================================================
	// Append to console
	// ============================================================

	function appendOutput(output, message) {
		if (
			output.textContent ===
			"No messages received."
		) {
			output.textContent = "";
		}

		if (output.textContent)
			output.textContent += "\\n\\n";

		output.textContent += message;

		output.scrollTop = output.scrollHeight;
	}


	// ============================================================
	// Operation ID
	// ============================================================

	function createOperationId(tag, path) {
		const safeTag = String(tag)
			.replace(/[^a-zA-Z0-9_-]/g, "_");

		const safePath = String(path)
			.replace(/[^a-zA-Z0-9_-]/g, "_");

		return `operations-${safeTag}-ws_${safePath}`;
	}
})();
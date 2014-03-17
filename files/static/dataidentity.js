/*
#   Copyright [2013] [M. David Allen]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
*/
function filePopup(hash, injectInto) { 
	$.getJSON("/hash/" + hash, function(data) {
		injectInto.html(data.names[0]);
	});
} // End filePopup

function toggle(id) { 
	var selector = "#" + id;
	if($(selector).is(":visible")) { $(selector).hide() } 
	else { $(selector).show(); } 
}

function showStats() { 
	$.get("/stats", function (data) {
		var str = "Currently tracking: " + data.files + " files<br>" + data.names + " filenames<br>" + 
		"and " + data.metadata + " metadata items."

		var d = $('<div id="StatsDialog">' + str + "</div>");
		d.dialog({
			title: "Statistics",
			position: { my: "center", at: "center", of: "viewport" }
		});		
		return false;
	});
}

function hashLookup(hashSelector) {
	var hash = $(hashSelector).val();

	if(!hash || hash.trim() == '') {
		alert("You must enter a valid hash");
		return false;
	}

	var url = "/hash/" + hash;

	$.ajax({
		url: url,
		cache: true, 
		type: 'get',
		error: function(XMLHttpRequest, textStatus, errorThrown) {
			alert("No file found by the hash " + hash);    		        
		},
		success: function(data){
			// It exists, so redirect there.
			window.location = url;
		}
	});

	return false;
}

function lookupMetadata(key, value) {
    window.location = "/files/" + key + "/" + val;
    return false;
}

function analysisDialog(urlsSelector) { 
	var num = Math.ceil(Math.random()*1000);
	var d = "dialog" + num;
	var p = "progress" + num;
	$("body").append("<div id='" + d + "'><div id='" + p + 
			"'><div class='progress-label'></div>" + 
	"</div><p></div>");

	$("#" + d).dialog({modal: true, title: 'Submitting URLs for Analysis...'});
	$(".progress-label").text("Please wait...");
	$("#" + p).progressbar({
		max: 100,
		value: 0,
		change: function() {
			$(".progress-label").text(
					$("#"+p).progressbar("value") + "%" );
		},

		complete: function() {
			$(".progress-label").text( "Complete!" );
		}});

	var urlTxt = $(urlsSelector).val();

	var urlArray = urlTxt.match(/[^\r\n]+/g);
	var total    = urlArray.length;
	var finished = 0;

	function signalItemFinished() { 
		finished = finished + 1;
		var pct = Math.ceil((finished/total)*100);
		$("#"+p).progressbar({value: pct});

		if(pct > 95) {
			$("#"+d).append(
					"<p><a href='/queue'>Check the queue</a></p>"                  
			);
		}
	}

	for(var x=0; x<urlArray.length; x++) { 
		var url = urlArray[x];
		url = url.trim();
		if(url == null || url == '' || url == 'null') { 
			total--; // This one doesn't count to total progress.
			continue; 
		} else if(url.match(/\/\/[^:]+:[^\@]\@/)) {
			$("#"+d).append("<p>URL " + url + 
			" contains a password.  Skipping.");
			signalItemFinished();
			continue;
		} else if(url.match(/\?/)) { 
			$("#"+d).append("<p>URL " + url + 
			" contains a query.  Skipping.");
			signalItemFinished();
			continue;
		} else if(url.match(/\#/)) { 
			$("#"+d).append("<p>URL " + url + 
			"contains a fragment.  Skipping.");
			signalItemFinished();
			continue;
		} 

		$("#"+d).dialog({title: "Submitting URLs..."});

		var callbackURL = url;
		$.ajax({url: "/analyze",
			type: 'POST',
			data: {'url' : callbackURL}, 
			success: function(data) { 
				if(data.md5) {
					// If the item has already been analyzed, the service
					// will return its data.  Just link back to the full details.
					$("#"+d).append(
							"<p>" + data.names[0] + " - " + 
							"<a href='/hash/" + data.md5 + "'>" + 
							"Results</a>"
					);
				} else if(data.message) {
					// If the item has been submitted to the queue, it will give us a
					// message back.
					$("#"+d).append(
							"<p>" + data.message + "</p>"
					);
				} else {            
					// otherwise there will be an error message.
					$("#"+d).append("<p><strong>Error:</strong> " + 
							callbackURL + " - " + data.error);
				} 

				signalItemFinished();
			},

			error: function(jqXHR, txtStatus, errorThrown) { 
				$("#"+d).dialog({title: "Failure"});
				$("#"+d).append("<p><strong>Failed</strong>: " + 
						callbackURL + 
						" - " + txtStatus);
				signalItemFinished();
			}
		});
	} 
} 

(function ($) {
	$.fn.styleTable = function (options) {
		var defaults = {
				css: 'styleTable'
		};
		options = $.extend(defaults, options);

		return this.each(function () {
			input = $(this);
			input.addClass(options.css);

			/*
			input.find("tr").live('mouseover mouseout', function (event) {
				if (event.type == 'mouseover') {
					$(this).children("td").addClass("ui-state-hover");
				} else {
					$(this).children("td").removeClass("ui-state-hover");
				}
			});
			*/

			input.find("th").addClass("ui-state-default");
			input.find("td").addClass("ui-widget-content");

			input.find("tr").each(function () {
				$(this).children("td:not(:first)").addClass("first");
				$(this).children("th:not(:first)").addClass("first");
			});
		});
	};
})(jQuery);
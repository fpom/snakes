function addcss (css) {
    $("head").append("<style type='text/css'>" + css + "</style>");
}

function addjs (js) {
    $("head").append("<script type='text/javascript'>" + js + "</script>");
}

function dialog (content) {
    $("#dialog").html(content);
    $("#dialog").append("<a href='#' id='dialog-close'>close</a>");
    $("#dialog-close").click(function() {
        $("#dialog-bg").hide();
        $("#dialog").hide();
    });
    $("#dialog").fadeTo(50, 1);
    $("#dialog-bg").fadeTo(50, 0.5);
}

var update = {
    settext : function (action) {
        $(action.select).text(action.text);
    },
    sethtml : function (action) {
        $(action.select).html(action.html);
    },
    clear : function (action) {
        $(action.select).html("");
    },
    setlist : function (action) {
        ul = $(action.select);
        ul.html("");
        $.each(action.items, function (num, item) {
            ul.append("<li>" + item + "</li>");
        });
    },
    dropclass : function (action) {
        $(action.select).removeClass(action.class);
    },
    addclass : function (action) {
        $(action.select).addClass(action.class);
    },
}

function setstate (state) {
    $("#trace").append("<div class='state'>" + state.id + "</div>");
    $.each(state.states, function (num, item) {
        update[item.do](item);
    });
    $.each(state.modes, function (num, action) {
        ul = $(action.select);
        ul.html("");
        $.each(action.items, function (pos, item) {
            ul.append("<li><a href='#'>" + item.html + "</a></li>");
                
            a = ul.children().last().children().first();
            a.attr({"data-state" : item.state, "data-mode" : item.mode});
            a.click(function () {
                state = $(this).attr("data-state");
                mode = $(this).attr("data-mode");
                content = $(this).html();
                $("#trace").append("<div class='mode'>" + content + "</div></div>");
                $.get("succ", {state: state, mode: mode},
                      function (newstate) {
                          setstate(newstate);
                      });
            });
        });
    });
}

$(document).ready(function() {
    /*
     * ping server every 10 seconds
     */
    $("#alive .ping").text("Stayin alive!");
    $.periodic({period: 10000, decay:1, max_period: 10000}, function() {
        $.get("ping", function(data) {
            $("#alive .ping").text(data);
        });
    });
    /*
     * setup UI and model
     */
    $.get("init", function(init) {
        /* bind reset button */
        $("#ui-reset").click(function() {
            $.get("init", {state: 0}, function(data) {
                setstate(data.state);
                $("#trace").html("");
            });
        });
        /* bind quit button */
        $("#ui-quit").click(function() {
            $.get("quit", function(data) {
                $("#alive .ui").html("").text(data);
            });        
        });
        /* dialogs */
        $("body").append("<div id='dialog'>"
                         + "</div><div id='dialog-bg'></div>");
        /* build about */
        $("#about").children().addClass("dialog");
        $("#ui-about").click(function() {
            dialog($("#about").html());
        });
        /* extend menu */
        if (init.ui != undefined) {
            ui = $("#alive .ui");
            /* TODO: fix spacing between these buttons */
            $.each(init.ui, function(num, menu) {
                ui.append("<li><a id='" + menu.id
                          + "'href='" + menu.href + "'>"
                          + menu.label + "</a></li>");
                if (menu.script != undefined) {
                    ui.children().last().click(function() {
                        eval(menu.script);
                    });
                }
            });
        }
        /* build help */
        if (init.help != undefined) {
            $.each(init.help, function(key, text) {
                /* TODO: create help dic or whatever needed */
            });
            $("#ui-help").click(function() {
                /* TODO: show/hide tooltips for help */
            });
        } else {
            $("#ui-help").remove();
        }
        /* setup initial state */
        setstate(init.state);
    });
});

#[macro_use]
extern crate stdweb;
extern crate yew;
use yew::prelude::*;

use yew::{html, Component, ComponentLink, Html, Renderable, ShouldRender, services::ConsoleService};
use stdweb::web::event::{IDragEvent, IEvent};
use stdweb::unstable::{TryInto, TryFrom};
use stdweb::web::{INode, document, INonElementParentNode, Element};

pub struct Model {
    console: ConsoleService,
}

pub enum Msg {
    DragStart(u32, u32),
    Drag(DragStartEvent),
    AllowDrop(DragOverEvent),
    DoDrop(DragDropEvent),
}




impl Component for Model {
    type Message = Msg;
    type Properties = ();

    fn create(_: (), _: ComponentLink<Self>) -> Self {
        Model {
            console: ConsoleService::new(),
        }
    }

    // Some details omitted. Explore the examples to get more.
    fn update(&mut self, msg: Self::Message) -> ShouldRender {
        match msg {
            Msg::DragStart(x, y) => {
                self.console.log(&*[x.to_string(), y.to_string()].join(" "));
            }
            Msg::Drag(e) => {
                let target = e.target().unwrap();
                let id: String = js!(return @{target.as_ref()}.id).try_into().unwrap();
                e.data_transfer().unwrap().set_data("text", id.as_ref());
            }
            Msg::AllowDrop(e) => {
                e.prevent_default();
            }
            Msg::DoDrop(e) => {
                e.prevent_default();
                let data = e.data_transfer().unwrap().get_data("text");
                let destination = Element::try_from(e.target().expect("couldn't get target")).expect("couldn't convert to Element");
                destination.append_child(&document().get_element_by_id(&*data).unwrap());
            }
        }
        true
    }
}

fn view_square(row: u32, column: u32) -> Html<Model> {
    html! {
        <td
            ondragover=|e| Msg::AllowDrop(e),
            ondrop=|e| Msg::DoDrop(e),
            draggable="false",
        >
        <p 
            id= {format!{"drag{}{}", row, column}},
            ondragstart=|e| Msg::Drag(e), 
            draggable="true",
        >
            {["cell".to_string(), column.to_string(), row.to_string()].join(" ")}
        </p>
        </td>
    }
}

fn view_row(row: u32) -> Html<Model> {
    html! {
        <tr>
            {for (0..10).map(|column| {
                view_square(row, column)
            })}
        </tr>
    }
}

impl Renderable<Model> for Model {
    fn view(&self) -> Html<Self> {
        html! {
            <div>
                <div>
                    <h2>
                        {"TEST"}
                    </h2>
                </div>
                    <table>
                        {for (0..5).map(|row| {
                        view_row(row)
                        })}
                    </table>
            </div>
        }
    }
}

fn main() {
    yew::initialize();
    App::<Model>::new().mount_to_body();
    yew::run_loop();
}